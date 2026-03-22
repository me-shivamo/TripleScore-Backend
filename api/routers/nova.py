import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from asgiref.sync import sync_to_async

from api.deps import get_current_user
from api.schemas.nova import ChatRequest, HistoryResponse, MessageResponse, OnboardingStatusResponse
from api.services.ai.client import get_ai_provider
from api.services.nova.prompts import build_system_prompt
from api.services.nova.context_builder import build_nova_context
from api.services.nova.onboarding_parser import (
    detect_onboarding_complete,
    extract_holistic_onboarding_data,
    save_holistic_onboarding_data,
    complete_onboarding,
)
from apps.users.models import User

router = APIRouter()


@sync_to_async
def _get_history(user_id: str, limit: int = 20) -> list:
    from apps.nova.models import ChatMessage
    return list(
        ChatMessage.objects.filter(user_id=user_id)
        .order_by("-created_at")[:limit]
    )


@sync_to_async
def _save_message(user_id: str, role: str, content: str, metadata: dict | None = None) -> None:
    from apps.nova.models import ChatMessage
    ChatMessage.objects.create(
        id=uuid.uuid4().hex[:24],
        user_id=user_id,
        role=role,
        content=content,
        metadata=metadata,
    )


@sync_to_async
def _get_profile(user_id: str):
    from apps.users.models import UserProfile
    return UserProfile.objects.filter(user_id=user_id).first()


@sync_to_async
def _get_full_transcript(user_id: str) -> list[dict]:
    from apps.nova.models import ChatMessage
    msgs = ChatMessage.objects.filter(user_id=user_id).order_by("created_at")
    return [{"role": m.role.lower(), "content": m.content} for m in msgs]


async def _post_stream_processing(
    user_id: str,
    mode: str,
    full_response: list[str],
    is_onboarding: bool,
    real_message_count: int,
) -> None:
    response_text = "".join(full_response)

    await _save_message(user_id, "ASSISTANT", response_text, {"mode": mode})

    should_complete = is_onboarding and (
        detect_onboarding_complete(response_text) or real_message_count >= 14
    )

    if should_complete:
        transcript = await _get_full_transcript(user_id)
        try:
            extracted = await extract_holistic_onboarding_data(transcript)
            await save_holistic_onboarding_data(user_id, extracted)
        except Exception as e:
            print(f"Holistic onboarding extraction failed: {e}")

        await complete_onboarding(user_id)


@router.post("/chat")
async def nova_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
):
    message = request.message.strip()
    if not message:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Message required")

    mode = request.mode
    user_id = user.id

    # Fetch last 20 messages for context
    history = await _get_history(user_id, limit=20)
    history = list(reversed(history))  # oldest first

    messages = [
        {"role": msg.role.lower(), "content": msg.content}
        for msg in history
    ]
    messages.append({"role": "user", "content": message})

    # Save user message
    await _save_message(user_id, "USER", message)

    # Build Nova context and system prompt
    context = await build_nova_context(user_id)
    system_prompt = build_system_prompt(mode, context)

    ai = get_ai_provider()

    profile = await _get_profile(user_id)
    is_onboarding = mode == "ONBOARDING" and not (profile and profile.onboarding_completed)

    real_message_count = sum(
        1 for msg in history
        if msg.content != "__NOVA_INIT__"
        and "__NOVA_ONBOARDING_COMPLETE__" not in msg.content
    )

    collected: list[str] = []

    async def stream_and_collect():
        async for chunk in ai.stream_chat(messages, system_prompt):
            text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            collected.append(text)
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")

        # After stream ends, schedule post-processing as background task
        background_tasks.add_task(
            _post_stream_processing,
            user_id,
            mode,
            collected,
            is_onboarding,
            real_message_count,
        )

    return StreamingResponse(
        stream_and_collect(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Transfer-Encoding": "chunked",
            "X-Nova-Mode": mode,
        },
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(user: Annotated[User, Depends(get_current_user)]):
    history = await _get_history(user.id, limit=50)
    history = list(reversed(history))
    return HistoryResponse(
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                metadata=msg.metadata,
                created_at=msg.created_at,
            )
            for msg in history
        ]
    )


@router.get("/onboarding-status", response_model=OnboardingStatusResponse)
async def onboarding_status(user: Annotated[User, Depends(get_current_user)]):
    profile = await _get_profile(user.id)
    return OnboardingStatusResponse(
        onboarding_completed=profile.onboarding_completed if profile else False,
        onboarding_step=profile.onboarding_step if profile else 0,
    )
