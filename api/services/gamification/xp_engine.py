import uuid
from datetime import datetime, timezone
from asgiref.sync import sync_to_async


XP_TABLE: dict[str, int] = {
    "CORRECT_EASY": 5,
    "CORRECT_MEDIUM": 10,
    "CORRECT_HARD": 15,
    "PRACTICE_SESSION": 20,
    "MOCK_COMPLETED": 50,
    "MISSION_COMPLETED": 0,  # variable — set by mission.xp_reward
    "STREAK_BONUS": 10,
    "ONBOARDING_COMPLETE": 100,
    "DAILY_LOGIN": 5,
    "DIAGNOSTIC_COMPLETE": 50,  # base; submit adds correct_answer bonus
}


def get_xp_for_correct_answer(difficulty: str) -> int:
    return XP_TABLE.get(f"CORRECT_{difficulty}", 5)


def _get_level_from_xp(xp: int) -> int:
    """Simple level formula: every 500 XP = 1 level."""
    return max(1, xp // 500 + 1)


@sync_to_async
def _award_xp_sync(
    user_id: str,
    reason: str,
    xp_override: int | None = None,
    reference_id: str | None = None,
    accuracy_bonus: float | None = None,
) -> dict:
    from apps.gamification.models import Gamification, XPEvent
    from apps.analytics.models import DailyStats

    try:
        gamification = Gamification.objects.get(user_id=user_id)
    except Gamification.DoesNotExist:
        return {"xp_gained": 0, "new_xp": 0, "level_up": False}

    amount = xp_override if xp_override is not None else XP_TABLE.get(reason, 0)

    if reason == "PRACTICE_SESSION" and accuracy_bonus is not None:
        amount += round(accuracy_bonus * 30)

    if reason == "STREAK_BONUS":
        streak = gamification.current_streak
        if streak >= 30:
            amount *= 4
        elif streak >= 14:
            amount *= 3
        elif streak >= 7:
            amount *= 2

    old_xp = gamification.xp
    old_level = _get_level_from_xp(old_xp)
    new_xp = old_xp + amount
    new_level = _get_level_from_xp(new_xp)

    gamification.xp = new_xp
    gamification.level = new_level
    gamification.save()

    XPEvent.objects.create(
        id=uuid.uuid4().hex[:24],
        gamification=gamification,
        amount=amount,
        reason=reason,
        reference_id=reference_id,
    )

    # Update today's DailyStats
    today = datetime.now(tz=timezone.utc).date()
    daily, _ = DailyStats.objects.get_or_create(
        user_id=user_id,
        date=today,
        defaults={"id": uuid.uuid4().hex[:24]},
    )
    daily.xp_earned += amount
    daily.save()

    return {
        "xp_gained": amount,
        "new_xp": new_xp,
        "old_level": old_level,
        "new_level": new_level,
        "level_up": new_level > old_level,
    }


async def award_xp(
    user_id: str,
    reason: str,
    xp_override: int | None = None,
    reference_id: str | None = None,
    accuracy_bonus: float | None = None,
) -> dict:
    return await _award_xp_sync(
        user_id,
        reason,
        xp_override=xp_override,
        reference_id=reference_id,
        accuracy_bonus=accuracy_bonus,
    )
