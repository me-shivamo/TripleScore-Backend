from django.contrib import admin
from .models import TopicProgress, DailyStats, RevisionItem

admin.site.register(TopicProgress)
admin.site.register(DailyStats)
admin.site.register(RevisionItem)
