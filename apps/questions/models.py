from django.db import models
from apps.users.models import User


class Subject(models.TextChoices):
    PHYSICS = "PHYSICS", "Physics"
    CHEMISTRY = "CHEMISTRY", "Chemistry"
    MATH = "MATH", "Math"


class Difficulty(models.TextChoices):
    EASY = "EASY", "Easy"
    MEDIUM = "MEDIUM", "Medium"
    HARD = "HARD", "Hard"


class QuestionType(models.TextChoices):
    MCQ = "MCQ", "MCQ"
    INTEGER = "INTEGER", "Integer"


class Question(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    subject = models.CharField(max_length=16, choices=Subject.choices)
    chapter = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    content = models.TextField()
    question_type = models.CharField(max_length=16, choices=QuestionType.choices, default=QuestionType.MCQ)
    options = models.JSONField()  # [{"label": "A", "text": "..."}, ...]
    correct_option = models.CharField(max_length=32)  # label for MCQ, number string for INTEGER
    explanation = models.TextField()
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices)
    tags = models.JSONField(default=list)
    source = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "questions"
        indexes = [
            models.Index(fields=["subject", "chapter", "topic", "difficulty"]),
        ]

    def __str__(self):
        return f"{self.subject}/{self.chapter} ({self.difficulty})"


class QuestionAttempt(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="question_attempts")
    session = models.ForeignKey(
        "practice.PracticeSession",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempts")
    selected_option = models.CharField(max_length=32, null=True, blank=True)
    is_correct = models.BooleanField()
    time_taken_secs = models.IntegerField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "question_attempts"
        indexes = [
            models.Index(fields=["user", "question"]),
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"Attempt({self.question_id}, correct={self.is_correct})"
