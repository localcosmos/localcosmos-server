from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('<uuid:app_uuid>/push-notifications/register-device/', views.RegisterFCMDeviceView.as_view(),
        name='api_register_fcm_device'),
    path('<uuid:app_uuid>/push-notifications/deregister-device/', views.DeregisterFCMDeviceView.as_view(),
        name='api_deregister_fcm_device'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])