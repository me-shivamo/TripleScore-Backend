from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    mode: str = "COMPANION"


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata: dict | None
    created_at: datetime


class HistoryResponse(BaseModel):
    messages: list[MessageResponse]


class OnboardingStatusResponse(BaseModel):
    onboarding_completed: bool
    onboarding_step: int
