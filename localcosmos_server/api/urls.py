from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView

from . import views

urlpatterns = [
    # app unspecific
    path('', views.APIHome.as_view(), name='api_home'),
    path('user/manage/', views.ManageAccount.as_view()),
    path('user/delete/', views.DeleteAccount.as_view()),
    path('user/register/', views.RegisterAccount.as_view()),
    path('password/reset/', views.PasswordResetRequest.as_view()),
    # JSON WebToken
    path('token/', views.TokenObtainPairViewWithClientID.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    # app specific
    path('app/<uuid:app_uuid>/', views.AppAPIHome.as_view(), name='app_api_home'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'html'])
