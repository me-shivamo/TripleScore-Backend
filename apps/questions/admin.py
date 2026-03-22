from django.contrib import admin
from .models import Question, QuestionAttempt

admin.site.register(Question)
admin.site.register(QuestionAttempt)
