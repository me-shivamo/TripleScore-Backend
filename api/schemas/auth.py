from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    avatar_url: str | None
    onboarding_completed: bool
    created_at: datetime
