from django.db import models
from django.utils import timezone

from localcosmos_server.models import LocalcosmosUser, App

from fcm_django.models import FCMDevice


class PushReceivingDevice(models.Model):

    app = models.ForeignKey(App, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=255)
    fcm_device = models.OneToOneField(FCMDevice, on_delete=models.CASCADE, related_name='push_receiving_device')
    language_code = models.CharField(max_length=15, blank=True)

    def save(self, *args, **kwargs):
        if not self.language_code:
            self.language_code = self.app.primary_language
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.app} - device ({self.fcm_device})"
    
    class Meta:
        unique_together = ('app', 'client_id')


class PushNotificationLog(models.Model):

    STATUS_SUCCESS = 'success'
    STATUS_FAILURE = 'failure'
    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILURE, 'Failure'),
    ]
    
    app = models.ForeignKey(App, on_delete=models.CASCADE)

    recipients = models.CharField(max_length=1024, blank=True)
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    data = models.JSONField(null=True, blank=True)
    language_code = models.CharField(max_length=15, blank=True, default='')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    sent_by = models.ForeignKey(LocalcosmosUser, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        recipient_names = self.recipients if self.recipients else 'unknown'
        return f"[{self.sent_at:%Y-%m-%d %H:%M}] {self.status} → {recipient_names}: {self.title}"
