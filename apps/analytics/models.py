from django.db import models
from apps.users.models import User
from apps.questions.models import Subject


class TopicProgress(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="topic_progress")
    subject = models.CharField(max_length=16, choices=Subject.choices)
    chapter = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    total_attempted = models.IntegerField(default=0)
    total_correct = models.IntegerField(default=0)
    avg_time_secs = models.FloatField(default=0.0)
    mastery_score = models.FloatField(default=0.0)  # 0.0 - 1.0
    last_attempted = models.DateTimeField(null=True, blank=True)
    is_unlocked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "topic_progress"
        unique_together = [["user", "subject", "chapter", "topic"]]
        indexes = [
            models.Index(fields=["user", "subject"]),
        ]

    def __str__(self):
        return f"{self.subject}/{self.chapter}/{self.topic}"


class DailyStats(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField()
    readiness_score = models.IntegerField(null=True, blank=True)
    questions_attempted = models.IntegerField(default=0)
    questions_correct = models.IntegerField(default=0)
    study_minutes = models.IntegerField(default=0)
    xp_earned = models.IntegerField(default=0)
    missions_completed = models.IntegerField(default=0)

    class Meta:
        db_table = "daily_stats"
        unique_together = [["user", "date"]]
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"DailyStats({self.user.email}, {self.date})"


class RevisionItem(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="revision_items")
    topic_progress = models.ForeignKey(TopicProgress, on_delete=models.CASCADE, related_name="revision_items")
    next_review_at = models.DateTimeField()
    interval_days = models.IntegerField(default=1)
    ease_factor = models.FloatField(default=2.5)  # SM-2 algorithm
    repetitions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "revision_items"
        indexes = [
            models.Index(fields=["user", "next_review_at"]),
        ]

    def __str__(self):
        return f"Revision({self.topic_progress}, next={self.next_review_at})"
