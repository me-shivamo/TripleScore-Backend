from django.db import models


class User(models.Model):
    id = models.CharField(max_length=36, primary_key=True)  # cuid-style
    firebase_uid = models.CharField(max_length=128, unique=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.URLField(max_length=1024, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    exam_attempt_date = models.DateTimeField(null=True, blank=True)
    daily_study_hours = models.FloatField(null=True, blank=True)
    target_score = models.IntegerField(null=True, blank=True)
    previous_score = models.IntegerField(null=True, blank=True)
    confidence_level = models.IntegerField(null=True, blank=True)  # 1-10
    strong_subjects = models.JSONField(default=list)   # ["PHYSICS", "CHEMISTRY"]
    weak_subjects = models.JSONField(default=list)
    study_struggles = models.JSONField(default=list)   # ["exam panic", ...]
    motivational_state = models.TextField(null=True, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.IntegerField(default=0)
    study_workflow = models.JSONField(null=True, blank=True)  # Nova-generated plan
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"Profile({self.user.email})"
