from django.db import models
from apps.users.models import User
from apps.questions.models import Subject, Difficulty


class XPReason(models.TextChoices):
    PRACTICE_SESSION = "PRACTICE_SESSION", "Practice Session"
    CORRECT_ANSWER = "CORRECT_ANSWER", "Correct Answer"
    MOCK_COMPLETED = "MOCK_COMPLETED", "Mock Completed"
    MISSION_COMPLETED = "MISSION_COMPLETED", "Mission Completed"
    STREAK_BONUS = "STREAK_BONUS", "Streak Bonus"
    ONBOARDING_COMPLETE = "ONBOARDING_COMPLETE", "Onboarding Complete"
    DAILY_LOGIN = "DAILY_LOGIN", "Daily Login"
    DIAGNOSTIC_COMPLETE = "DIAGNOSTIC_COMPLETE", "Diagnostic Complete"


class MissionType(models.TextChoices):
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"


class BadgeRarity(models.TextChoices):
    COMMON = "COMMON", "Common"
    RARE = "RARE", "Rare"
    EPIC = "EPIC", "Epic"
    LEGENDARY = "LEGENDARY", "Legendary"


class Gamification(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="gamification")
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_active_date = models.DateTimeField(null=True, blank=True)
    total_study_mins = models.IntegerField(default=0)
    season_rank = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "gamification"

    def __str__(self):
        return f"Gamification({self.user.email}, xp={self.xp})"


class XPEvent(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    gamification = models.ForeignKey(Gamification, on_delete=models.CASCADE, related_name="xp_history")
    amount = models.IntegerField()
    reason = models.CharField(max_length=32, choices=XPReason.choices)
    reference_id = models.CharField(max_length=36, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "xp_events"

    def __str__(self):
        return f"XP+{self.amount} ({self.reason})"


class Mission(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=16, choices=MissionType.choices)
    xp_reward = models.IntegerField()
    target = models.IntegerField()
    metric = models.CharField(max_length=64)  # "questions_correct", "mock_completed"
    subject = models.CharField(max_length=16, choices=Subject.choices, null=True, blank=True)
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "missions"

    def __str__(self):
        return self.title


class UserMission(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="missions")
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="user_missions")
    progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "user_missions"
        indexes = [
            models.Index(fields=["user", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.mission.title}"


class Badge(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    icon_url = models.URLField(max_length=1024)
    condition = models.JSONField()  # {"type": "streak", "value": 7}
    xp_reward = models.IntegerField(default=0)
    rarity = models.CharField(max_length=16, choices=BadgeRarity.choices)

    class Meta:
        db_table = "badges"

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="user_badges")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_badges"
        unique_together = [["user", "badge"]]

    def __str__(self):
        return f"{self.user.email} - {self.badge.name}"
