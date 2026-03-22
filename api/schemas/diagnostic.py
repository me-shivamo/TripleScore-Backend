from pydantic import BaseModel
from datetime import datetime


class ChapterSuggestion(BaseModel):
    subject: str
    chapter: str


class ProfileInfo(BaseModel):
    name: str | None
    exam_attempt_date: datetime | None
    strong_subjects: list[str]
    weak_subjects: list[str]
    previous_score: int | None
    daily_study_hours: float | None


class DiagnosticStartResponse(BaseModel):
    already_done: bool
    profile: ProfileInfo | None = None
    strong_suggestion: ChapterSuggestion | None = None
    weak_suggestion: ChapterSuggestion | None = None
    chapters_by_subject: dict[str, list[str]] | None = None


class QuestionsRequest(BaseModel):
    subject: str
    chapter: str
    count: int = 10


class QuestionOption(BaseModel):
    label: str
    text: str


class QuestionOut(BaseModel):
    id: str
    subject: str
    chapter: str
    topic: str
    content: str
    question_type: str
    options: list[QuestionOption]
    difficulty: str


class QuestionsResponse(BaseModel):
    questions: list[QuestionOut]


class SubmitAttempt(BaseModel):
    question_id: str
    selected_option: str | None  # None = skipped
    time_taken_secs: int


class SubmitRequest(BaseModel):
    test_number: int  # 1 or 2
    subject: str
    chapter: str
    attempts: list[SubmitAttempt]


class SubmitResponse(BaseModel):
    score: dict  # {"correct": int, "total": int}
    mastery_score: float
    session_id: str
    xp_result: dict
