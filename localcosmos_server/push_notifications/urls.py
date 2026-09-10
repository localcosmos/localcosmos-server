from django.urls import path

from . import views

app_name = 'push_notifications'

urlpatterns = [
    path('<str:app_uid>/push-notifications/', views.ManagePushNotifications.as_view(),
         name='manage_push_notifications'),
    path('<str:app_uid>/push-notifications/send/', views.SendPushNotification.as_view(),
         name='send_push_notification'),
    path('<str:app_uid>/push-notifications/logs/', views.GetNotificationLogs.as_view(),
         name='get_notification_logs'),
    path('<str:app_uid>/push-notifications/send/modal/', views.SendPushNotificationModal.as_view(),
         name='send_push_notification_modal'),
]