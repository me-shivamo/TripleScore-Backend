from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from asgiref.sync import sync_to_async

from api.deps import get_current_user
from api.schemas.dashboard import DashboardResponse, GamificationData, TodayStats, MissionData, ProfileData
from api.services.analytics.readiness_calculator import calculate_readiness_score
from apps.users.models import User

router = APIRouter()


@sync_to_async
def _fetch_dashboard_data(user_id: str) -> dict:
    from apps.gamification.models import Gamification, UserMission
    from apps.analytics.models import DailyStats
    from apps.users.models import UserProfile

    today = datetime.now(tz=timezone.utc).date()

    try:
        gamification = Gamification.objects.get(user_id=user_id)
    except Gamification.DoesNotExist:
        gamification = None

    today_stats = DailyStats.objects.filter(user_id=user_id, date=today).first()

    try:
        profile = UserProfile.objects.get(user_id=user_id)
    except UserProfile.DoesNotExist:
        profile = None

    missions = list(
        UserMission.objects.filter(
            user_id=user_id,
            expires_at__gte=datetime.now(tz=timezone.utc),
        )
        .select_related("mission")
        .order_by("-assigned_at")[:5]
    )

    return {
        "gamification": gamification,
        "today_stats": today_stats,
        "profile": profile,
        "missions": missions,
    }


@router.get("", response_model=DashboardResponse)
async def get_dashboard(user: Annotated[User, Depends(get_current_user)]):
    data = await _fetch_dashboard_data(user.id)
    gamification = data["gamification"]
    today_stats = data["today_stats"]
    profile = data["profile"]
    missions = data["missions"]

    # Calculate readiness score if not cached today
    readiness_score = today_stats.readiness_score if today_stats else None
    if readiness_score is None:
        readiness_score = await calculate_readiness_score(user.id)

    # Days until exam
    days_until_exam = None
    if profile and profile.exam_attempt_date:
        exam_dt = profile.exam_attempt_date
        if exam_dt.tzinfo is None:
            exam_dt = exam_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        days_until_exam = max(0, (exam_dt - now).days)

    return DashboardResponse(
        readiness_score=readiness_score,
        days_until_exam=days_until_exam,
        gamification=GamificationData(
            xp=gamification.xp if gamification else 0,
            level=gamification.level if gamification else 1,
            current_streak=gamification.current_streak if gamification else 0,
            longest_streak=gamification.longest_streak if gamification else 0,
        ),
        today_stats=TodayStats(
            questions_attempted=today_stats.questions_attempted if today_stats else 0,
            questions_correct=today_stats.questions_correct if today_stats else 0,
            study_minutes=today_stats.study_minutes if today_stats else 0,
            xp_earned=today_stats.xp_earned if today_stats else 0,
        ),
        missions=[
            MissionData(
                id=um.id,
                title=um.mission.title,
                description=um.mission.description,
                xp_reward=um.mission.xp_reward,
                progress=um.progress,
                target=um.mission.target,
                completed=um.completed,
                type=um.mission.type,
            )
            for um in missions
        ],
        profile=ProfileData(
            onboarding_completed=profile.onboarding_completed if profile else False,
            strong_subjects=list(profile.strong_subjects) if profile else [],
            weak_subjects=list(profile.weak_subjects) if profile else [],
        ),
    )
