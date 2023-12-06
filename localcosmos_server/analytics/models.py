from django.db import models

from localcosmos_server.models import App
'''
Frontends should have the ability to log certain events
These log must be anonymous at all costs and may never contain
any form of unique identifier like IP addresses
'''
class AnonymousLog(models.Model):
    app = models.ForeignKey(App, to_field='uuid', on_delete=models.CASCADE)
    app_version = models.CharField(max_length=100, null=True)
    event_type = models.CharField(max_length=355)
    event_content = models.CharField(max_length=355)
    platform = models.CharField(max_length=100, null=True)

    created_at = models.DateTimeField(auto_now_add=True)