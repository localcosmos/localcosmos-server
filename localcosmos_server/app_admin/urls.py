from django.urls import include, path

from django.conf import settings
from . import views

app_name = 'app_admin'

urlpatterns = [
    path('<str:app_uid>/', views.AdminHome.as_view(), name='home'),
    path('<str:app_uid>/users/', views.UserList.as_view(), name='user_list'),
    path('<str:app_uid>/users/<int:user_id>/role', views.ManageAppUserRole.as_view(), name='manage_app_user_role'),
    path('<str:app_uid>/users/search', views.SearchAppUser.as_view(), name='search_app_user'),
]
