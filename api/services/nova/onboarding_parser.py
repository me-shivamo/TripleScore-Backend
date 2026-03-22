import json
import uuid
from datetime import datetime, timezone
from asgiref.sync import sync_to_async

from api.services.ai.client import get_ai_provider
from .prompts import build_workflow_generation_prompt


def detect_onboarding_complete(assistant_message: str) -> bool:
    """Pure string check — zero AI cost."""
    return "__NOVA_ONBOARDING_COMPLETE__" in assistant_message


async def _collect_stream(gen) -> str:
    """Collect an async byte generator into a single string."""
    chunks = []
    async for chunk in gen:
        chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


async def extract_holistic_onboarding_data(
    transcript: list[dict],  # [{"role": "user"|"assistant", "content": str}]
) -> dict:
    ai = get_ai_provider()

    filtered = [
        m for m in transcript
        if m["content"] != "__NOVA_INIT__"
        and "__NOVA_ONBOARDING_COMPLETE__" not in m["content"]
    ]

    transcript_text = "\n\n".join(
        f"{'Student' if m['role'] == 'user' else 'Nova'}: {m['content']}"
        for m in filtered
    )

    prompt = f"""Extract structured data from this JEE student onboarding conversation.

CONVERSATION:
{transcript_text}

Return ONLY valid JSON with no extra text:
{{
  "examDate": "YYYY-MM-DD or null",
  "strongSubjects": ["PHYSICS", "CHEMISTRY", "MATH"],
  "weakSubjects": ["PHYSICS", "CHEMISTRY", "MATH"],
  "dailyStudyHours": number or null,
  "previousScore": number 0-300 or null,
  "confidenceLevel": number 1-10 or null,
  "studyStruggles": ["short phrase per struggle the student mentioned"],
  "motivationalState": "one sentence describing their emotional or motivational state, or null"
}}

Rules:
- examDate: convert "April 2025" or "JEE 2026" to YYYY-MM-DD using the 1st of the month
- subjects: only include what the student explicitly stated, not Nova's inferences
- studyStruggles: use the student's own words closely, keep each entry brief
- Set null or empty array [] for any field that cannot be determined from the conversation"""

    messages = [{"role": "user", "content": prompt}]
    raw = await _collect_stream(ai.stream_chat(messages, "You are a precise data extractor. Return only valid JSON."))

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


@sync_to_async
def _save_profile_data(user_id: str, data: dict) -> None:
    from apps.users.models import User, UserProfile

    user = User.objects.get(id=user_id)
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"id": uuid.uuid4().hex[:24]},
    )

    if data.get("examDate"):
        try:
            profile.exam_attempt_date = datetime.strptime(data["examDate"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if data.get("strongSubjects"):
        profile.strong_subjects = data["strongSubjects"]
    if data.get("weakSubjects"):
        profile.weak_subjects = data["weakSubjects"]
    if data.get("dailyStudyHours") is not None:
        profile.daily_study_hours = data["dailyStudyHours"]
    if data.get("previousScore") is not None:
        profile.previous_score = data["previousScore"]
    if data.get("confidenceLevel") is not None:
        profile.confidence_level = data["confidenceLevel"]
    if data.get("studyStruggles"):
        profile.study_struggles = data["studyStruggles"]
    if data.get("motivationalState"):
        profile.motivational_state = data["motivationalState"]

    profile.save()


@sync_to_async
def _complete_onboarding_db(user_id: str, study_workflow: dict) -> None:
    from apps.users.models import User, UserProfile
    from apps.gamification.models import Gamification, XPEvent

    user = User.objects.get(id=user_id)
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"id": uuid.uuid4().hex[:24]},
    )
    profile.study_workflow = study_workflow
    profile.onboarding_completed = True
    profile.onboarding_step = 6
    profile.save()

    # Award 100 XP for completing onboarding
    try:
        gamification = Gamification.objects.get(user=user)
        gamification.xp += 100
        gamification.save()
        XPEvent.objects.create(
            id=uuid.uuid4().hex[:24],
            gamification=gamification,
            amount=100,
            reason="ONBOARDING_COMPLETE",
        )
    except Gamification.DoesNotExist:
        pass


async def save_holistic_onboarding_data(user_id: str, data: dict) -> None:
    await _save_profile_data(user_id, data)


async def complete_onboarding(user_id: str) -> None:
    from apps.users.models import User, UserProfile
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_profile() -> dict | None:
        try:
            user = User.objects.select_related("profile").get(id=user_id)
            p = user.profile
            return {
                "exam_date": p.exam_attempt_date.strftime("%Y-%m-%d") if p.exam_attempt_date else "unknown",
                "strong_subjects": list(p.strong_subjects or []),
                "weak_subjects": list(p.weak_subjects or []),
                "daily_hours": p.daily_study_hours or 4,
                "previous_score": p.previous_score,
                "confidence_level": p.confidence_level,
                "study_struggles": list(p.study_struggles or []),
                "motivational_state": p.motivational_state,
            }
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            return None

    profile_data = await get_profile()
    if not profile_data:
        return

    prompt = build_workflow_generation_prompt(profile_data)
    ai = get_ai_provider()

    try:
        messages = [{"role": "user", "content": prompt}]
        raw = await _collect_stream(
            ai.stream_chat(messages, "You are a study planner. Return only valid JSON.")
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        study_workflow = json.loads(raw.strip())
    except Exception:
        study_workflow = {"summary": "Focus on your weak subjects daily with consistent practice."}

    await _complete_onboarding_db(user_id, study_workflow)
