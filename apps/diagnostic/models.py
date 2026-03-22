from django.db import models
from apps.users.models import User


class DiagnosticStatus(models.TextChoices):
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    TEST1_COMPLETE = "TEST1_COMPLETE", "Test 1 Complete"
    COMPLETED = "COMPLETED", "Completed"
    SKIPPED = "SKIPPED", "Skipped"


class DiagnosticSession(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="diagnostic_session")
    status = models.CharField(
        max_length=24, choices=DiagnosticStatus.choices, default=DiagnosticStatus.IN_PROGRESS
    )
    test1_session_id = models.CharField(max_length=36, null=True, blank=True)
    test2_session_id = models.CharField(max_length=36, null=True, blank=True)
    test1_subject = models.CharField(max_length=16, null=True, blank=True)
    test1_chapter = models.CharField(max_length=255, null=True, blank=True)
    test2_subject = models.CharField(max_length=16, null=True, blank=True)
    test2_chapter = models.CharField(max_length=255, null=True, blank=True)
    skipped = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "diagnostic_sessions"

    def __str__(self):
        return f"DiagnosticSession({self.user.email}, {self.status})"
