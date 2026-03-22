from typing import Annotated
from fastapi import APIRouter, Depends
from asgiref.sync import sync_to_async

from api.deps import get_current_user
from api.schemas.auth import UserResponse
from apps.users.models import User

router = APIRouter()


@sync_to_async
def _get_onboarding_status(user: User) -> bool:
    try:
        return user.profile.onboarding_completed
    except Exception:
        return False


@router.post("/login", response_model=UserResponse)
async def login(user: Annotated[User, Depends(get_current_user)]):
    """
    Verify Firebase ID token, upsert user in DB, and return user info.
    The frontend calls this once after Firebase Google sign-in.
    """
    onboarding_completed = await _get_onboarding_status(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        onboarding_completed=onboarding_completed,
        created_at=user.created_at,
    )
