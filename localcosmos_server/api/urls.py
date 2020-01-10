from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    # app unspecific
    path('', views.APIHome.as_view(), name='api_home'),
    path('auth-token/', views.ObtainLCAuthToken.as_view()),
    path('user/<int:user_id>/manage/', views.ManageAccount.as_view()),
    path('user/<int:user_id>/delete/', views.DeleteAccount.as_view()),
    path('user/register/', views.RegisterAccount.as_view()),
    # app specific
    path('app/<uuid:app_uuid>/', views.AppAPIHome.as_view(), name='app_api_home'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'html'])
