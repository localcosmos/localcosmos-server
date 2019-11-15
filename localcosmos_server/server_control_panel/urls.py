from django.urls import include, path

from django.conf import settings
from . import views

app_name = 'server_control_panel'

urlpatterns = [
    path('', views.ServerControlPanelHome.as_view(), name='home'),
    path('app/install/', views.InstallApp.as_view(), name='install_app'),
    path('app/<str:app_uid>/', views.AppDetail.as_view(), name='app_detail'),
    path('app/<str:app_uid>/update/', views.UpdateApp.as_view(), name='update_app'),
    path('app/<str:app_uid>/api-status/', views.CheckAppApiStatus.as_view(), name='app_api_status'),
]
