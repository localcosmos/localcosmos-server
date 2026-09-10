from django.contrib import admin

from .models import PushNotificationLog


@admin.register(PushNotificationLog)
class PushNotificationLogAdmin(admin.ModelAdmin):
    list_display = ('sent_at', 'status', 'app', 'recipients', 'title')
    list_filter = ('status', 'app', 'sent_at')
    search_fields = ('recipients', 'title', 'body')
    readonly_fields = ('sent_at', 'app', 'recipients', 'title', 'body', 'data', 'language_code', 'status', 'error_message')
