from datetime import datetime, timezone, timedelta
from asgiref.sync import sync_to_async

from .prompts import NovaContext


@sync_to_async
def _fetch_nova_data(user_id: str) -> dict:
    from apps.users.models import User
    from apps.gamification.models import Gamification
    from apps.analytics.models import DailyStats
    from apps.practice.models import MockTest

    try:
        user = User.objects.select_related("profile").get(id=user_id)
    except User.DoesNotExist:
        return {}

    try:
        gamification = Gamification.objects.get(user=user)
    except Gamification.DoesNotExist:
        gamification = None

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)
    recent_stats = list(
        DailyStats.objects.filter(user=user, date__gte=cutoff.date()).order_by("-date")[:7]
    )

    last_mock = MockTest.objects.filter(user=user).order_by("-attempt_date").first()

    today = datetime.now(tz=timezone.utc).date()
    tomorrow = today + timedelta(days=1)

    from apps.gamification.models import UserMission
    completed_missions = UserMission.objects.filter(
        user=user, completed=True, expires_at__gte=datetime.combine(today, datetime.min.time())
    ).count()
    total_missions = UserMission.objects.filter(
        user=user,
        expires_at__gte=datetime.combine(today, datetime.min.time()),
        expires_at__lt=datetime.combine(tomorrow, datetime.min.time()),
    ).count()

    return {
        "user": user,
        "gamification": gamification,
        "recent_stats": recent_stats,
        "last_mock": last_mock,
        "completed_missions": completed_missions,
        "total_missions": total_missions,
    }


async def build_nova_context(user_id: str) -> NovaContext:
    data = await _fetch_nova_data(user_id)
    if not data:
        return NovaContext()

    user = data["user"]
    gamification = data["gamification"]
    recent_stats = data["recent_stats"]
    last_mock = data["last_mock"]

    context = NovaContext(user_name=user.name)

    profile = getattr(user, "profile", None)
    if profile and profile.exam_attempt_date:
        exam_dt = profile.exam_attempt_date
        if exam_dt.tzinfo is None:
            exam_dt = exam_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        days_until = max(0, (exam_dt - now).days)
        context.exam_date = exam_dt.strftime("%B %Y")
        context.days_until_exam = days_until
        context.strong_subjects = list(profile.strong_subjects or [])
        context.weak_subjects = list(profile.weak_subjects or [])

    if profile:
        if profile.study_struggles:
            context.study_struggles = list(profile.study_struggles)
        if profile.motivational_state:
            context.motivational_state = profile.motivational_state

    if gamification:
        context.current_streak = gamification.current_streak

    if recent_stats:
        total_correct = sum(s.questions_correct for s in recent_stats)
        total_attempted = sum(s.questions_attempted for s in recent_stats)
        if total_attempted > 0:
            context.readiness_score = round((total_correct / total_attempted) * 100)

    if last_mock and last_mock.total_marks:
        context.last_mock_score = last_mock.total_marks

    context.missions_completed = data["completed_missions"]
    context.total_missions = data["total_missions"]

    return context
