from django.contrib import admin
from .models import Gamification, XPEvent, Mission, UserMission, Badge, UserBadge

admin.site.register(Gamification)
admin.site.register(XPEvent)
admin.site.register(Mission)
admin.site.register(UserMission)
admin.site.register(Badge)
admin.site.register(UserBadge)
