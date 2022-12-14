from django.urls import include, path
from django.contrib.auth import views as auth_views

from . import views

# THESE URLS APPEAR IN BOTH TENANT AND PUBLIC URLCONF

urlpatterns = [
    # essentials
    path('log-in/', views.LogIn.as_view(extra_context={'base_template': 'base.html'}), name='log_in'),
    path('log-out/', auth_views.LogoutView.as_view(extra_context={'base_template': 'base.html'}), name='log_out'),
    path('loggedout/', views.LoggedOut.as_view(extra_context={'base_template': 'base.html'}), name='loggedout'),

    path('password-change/', auth_views.PasswordChangeView.as_view(
        extra_context={'base_template': 'base.html'},
        template_name='localcosmos_server/registration/password_change_form.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        extra_context={'base_template': 'base.html'},
        template_name='localcosmos_server/registration/password_change_done.html'), name='password_change_done'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(
        extra_context={'base_template': 'base.html'},
        template_name='localcosmos_server/registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        extra_context={'base_template': 'base.html'},
        template_name='localcosmos_server/registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        extra_context={'base_template': 'base.html'},
        template_name='localcosmos_server/registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        extra_context={'base_template': 'base.html'},
        template_name='localcosmos_server/registration/password_reset_complete.html'),
        name='password_reset_complete'),
    # server content images
    path('manage-server-content-image/<int:content_type_id>/<int:object_id>/',
        views.ManageServerContentImage.as_view(), name='manage_server_content_image'),
    path('manage-server-content-image/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageServerContentImage.as_view(), name='manage_server_content_image'),
    path('manage-server-content-image/<int:content_image_id>/',
        views.ManageServerContentImage.as_view(), name='manage_server_content_image'),
    path('delete-server-content-image/<int:pk>/',
        views.DeleteServerContentImage.as_view(), name='delete_server_content_image'),
    # SETUP GUI
    path('', include('localcosmos_server.setup_urls')),
    
    # SERVER CONTROL PANEL
    path('control-panel/', include('localcosmos_server.server_control_panel.urls', namespace='scp')),

    # LEGAL
    path('legal-notice/<str:app_uid>/', views.LegalNotice.as_view(), name='legal_notice'),
    path('privacy-statement/<str:app_uid>/', views.PrivacyStatement.as_view(), name='privacy_statement'),
    
]
