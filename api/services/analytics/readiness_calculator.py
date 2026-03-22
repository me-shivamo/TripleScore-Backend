import uuid
from datetime import datetime, timezone, timedelta
from asgiref.sync import sync_to_async


@sync_to_async
def _calculate_sync(user_id: str) -> int:
    from apps.analytics.models import TopicProgress, DailyStats
    from apps.gamification.models import Gamification

    topic_progress = list(TopicProgress.objects.filter(user_id=user_id))
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=14)).date()
    recent_stats = list(DailyStats.objects.filter(user_id=user_id, date__gte=cutoff))

    try:
        gamification = Gamification.objects.get(user_id=user_id)
    except Gamification.DoesNotExist:
        gamification = None

    # 1. Accuracy Score (0-100)
    accuracy_score = 0.0
    topics_with_attempts = [t for t in topic_progress if t.total_attempted > 0]
    if topics_with_attempts:
        total_correct = sum(t.total_correct for t in topics_with_attempts)
        total_attempted = sum(t.total_attempted for t in topics_with_attempts)
        if total_attempted > 0:
            accuracy_score = (total_correct / total_attempted) * 100

    # 2. Speed Score (0-100) — benchmark: 180 sec/question
    speed_score = 0.0
    topics_with_time = [t for t in topic_progress if t.avg_time_secs > 0]
    if topics_with_time:
        avg_time = sum(t.avg_time_secs for t in topics_with_time) / len(topics_with_time)
        speed_score = min((180 / avg_time) * 100, 100)

    # 3. Syllabus Coverage (0-100)
    TOTAL_JEE_TOPICS = 90
    mastered = sum(1 for t in topic_progress if t.mastery_score >= 0.5)
    syllabus_coverage = (mastered / TOTAL_JEE_TOPICS) * 100

    # 4. Consistency Score (0-100)
    active_days = sum(1 for s in recent_stats if s.questions_attempted > 0)
    consistency_score = (active_days / 14) * 100
    streak = gamification.current_streak if gamification else 0
    streak_bonus = min(streak / 3, 10)
    consistency_score = min(consistency_score + streak_bonus, 100)

    readiness_score = round(
        0.35 * accuracy_score
        + 0.20 * speed_score
        + 0.30 * syllabus_coverage
        + 0.15 * consistency_score
    )

    # Save to today's DailyStats
    today = datetime.now(tz=timezone.utc).date()
    daily, _ = DailyStats.objects.get_or_create(
        user_id=user_id,
        date=today,
        defaults={"id": uuid.uuid4().hex[:24]},
    )
    daily.readiness_score = readiness_score
    daily.save()

    return readiness_score


async def calculate_readiness_score(user_id: str) -> int:
    return await _calculate_sync(user_id)
