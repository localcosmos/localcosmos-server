from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('<uuid:app_uuid>/anonymous-log-entry/', views.CreateAnonymousLogEntry.as_view(),
        name='api_create_anonymous_log_entry'),
    path('<uuid:app_uuid>/anonymous-log/get-event-count/', views.GetEventCounts.as_view(),
        name='api_get_anonymous_log_event_count'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])