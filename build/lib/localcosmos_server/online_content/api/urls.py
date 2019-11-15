from django.urls import include, path
from . import views
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = [
    path('online-content/', views.GetOnlineContent.as_view(), name='get_online_content'), # HTML ONLY
    path('online-content/list/', views.GetOnlineContentList.as_view(), # JSON ONLY
         name='get_online_content_list'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
