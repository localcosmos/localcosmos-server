from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView

from . import views

urlpatterns = [
    # app unspecific
    path('', views.APIHome.as_view(), name='api_home'),
    path('<uuid:app_uuid>/user/', views.ManageAccount.as_view(), name='api_manage_account'),
    path('<uuid:app_uuid>/user/register/', views.RegisterAccount.as_view(), name='api_register_account'),
    path('<uuid:app_uuid>/password/reset/', views.PasswordResetRequest.as_view(), name='api_password_reset'),
    # JSON WebToken
    path('<uuid:app_uuid>/token/', views.TokenObtainPairViewWithClientID.as_view(), name='token_obtain_pair'),
    path('<uuid:app_uuid>/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('<uuid:app_uuid>/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    # app specific
    path('<uuid:app_uuid>/', views.AppAPIHome.as_view(), name='app_api_home'),
    path('<uuid:app_uuid>/anycluster/', include('localcosmos_server.api.anycluster_schema_urls')),
    # content images
    path('<uuid:app_uuid>/content-image/', views.ManageServerContentImage.as_view(), name='api_server_content_image'),
    path('<uuid:app_uuid>/content-image/<str:model>/<int:object_id>/<str:image_type>/', views.ManageServerContentImage.as_view(),
        name='api_server_content_image'),
    path('<uuid:app_uuid>/content-image/<int:pk>/', views.ManageServerContentImage.as_view(),
        name='api_server_content_image'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
