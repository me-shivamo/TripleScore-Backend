from pydantic import BaseModel
from datetime import datetime


class GamificationData(BaseModel):
    xp: int
    level: int
    current_streak: int
    longest_streak: int


class TodayStats(BaseModel):
    questions_attempted: int
    questions_correct: int
    study_minutes: int
    xp_earned: int


class MissionData(BaseModel):
    id: str
    title: str
    description: str
    xp_reward: int
    progress: int
    target: int
    completed: bool
    type: str


class ProfileData(BaseModel):
    onboarding_completed: bool
    strong_subjects: list[str]
    weak_subjects: list[str]


class DashboardResponse(BaseModel):
    readiness_score: int | None
    days_until_exam: int | None
    gamification: GamificationData
    today_stats: TodayStats
    missions: list[MissionData]
    profile: ProfileData
