from django.db import models
from apps.users.models import User
from apps.questions.models import Subject


class SessionMode(models.TextChoices):
    TOPIC = "TOPIC", "Topic"
    TIMED = "TIMED", "Timed"
    ADAPTIVE = "ADAPTIVE", "Adaptive"
    MOCK_REVIEW = "MOCK_REVIEW", "Mock Review"


class AnalysisStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class PracticeSession(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="practice_sessions")
    subject = models.CharField(max_length=16, choices=Subject.choices, null=True, blank=True)
    chapter = models.CharField(max_length=255, null=True, blank=True)
    topic = models.CharField(max_length=255, null=True, blank=True)
    mode = models.CharField(max_length=16, choices=SessionMode.choices)
    total_questions = models.IntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_secs = models.IntegerField(null=True, blank=True)
    xp_earned = models.IntegerField(default=0)

    class Meta:
        db_table = "practice_sessions"
        indexes = [
            models.Index(fields=["user", "started_at"]),
        ]

    def __str__(self):
        return f"Session({self.user_id}, {self.mode})"


class MockTest(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mock_tests")
    test_name = models.CharField(max_length=255)
    attempt_date = models.DateTimeField()
    total_questions = models.IntegerField(default=90)
    attempted = models.IntegerField()
    correct = models.IntegerField()
    incorrect = models.IntegerField()
    skipped = models.IntegerField()
    physics_score = models.IntegerField(null=True, blank=True)
    chemistry_score = models.IntegerField(null=True, blank=True)
    math_score = models.IntegerField(null=True, blank=True)
    total_marks = models.IntegerField(null=True, blank=True)
    max_marks = models.IntegerField(default=300)
    time_taken_mins = models.IntegerField(null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)
    ai_analysis = models.JSONField(null=True, blank=True)
    analysis_status = models.CharField(
        max_length=16, choices=AnalysisStatus.choices, default=AnalysisStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mock_tests"
        indexes = [
            models.Index(fields=["user", "attempt_date"]),
        ]

    def __str__(self):
        return f"Mock({self.test_name})"
