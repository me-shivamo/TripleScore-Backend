from datetime import datetime, timezone, timedelta
from asgiref.sync import sync_to_async


@sync_to_async
def _update_streak_sync(user_id: str) -> dict:
    from apps.gamification.models import Gamification

    try:
        gamification = Gamification.objects.get(user_id=user_id)
    except Gamification.DoesNotExist:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "streak_maintained": False,
            "streak_broken": False,
        }

    today = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    last_active = gamification.last_active_date
    if last_active and last_active.tzinfo is None:
        last_active = last_active.replace(tzinfo=timezone.utc)
    if last_active:
        last_active = last_active.replace(hour=0, minute=0, second=0, microsecond=0)

    streak_maintained = False
    streak_broken = False

    if not last_active:
        new_streak = 1
    elif last_active == today:
        return {
            "current_streak": gamification.current_streak,
            "longest_streak": gamification.longest_streak,
            "streak_maintained": True,
            "streak_broken": False,
        }
    elif last_active == yesterday:
        new_streak = gamification.current_streak + 1
        streak_maintained = True
    else:
        new_streak = 1
        streak_broken = True

    new_longest = max(new_streak, gamification.longest_streak)
    gamification.current_streak = new_streak
    gamification.longest_streak = new_longest
    gamification.last_active_date = today
    gamification.save()

    return {
        "current_streak": new_streak,
        "longest_streak": new_longest,
        "streak_maintained": streak_maintained,
        "streak_broken": streak_broken,
        "award_bonus": streak_maintained or new_streak > 1,
    }


async def update_streak(user_id: str) -> dict:
    result = await _update_streak_sync(user_id)

    if result.get("award_bonus"):
        from api.services.gamification.xp_engine import award_xp
        await award_xp(user_id, "STREAK_BONUS")

    return result
