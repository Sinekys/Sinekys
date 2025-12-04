from django.contrib import admin
from .models import DailyQuota

@admin.register(DailyQuota)
class DailyQuotaAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'attempts_count', 'messages_count')
    list_filter = ('date',)
