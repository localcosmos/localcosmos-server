from django.urls import include, path
from . import views
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = [
    path('<uuid:app_uuid>/template-content/<str:slug>/', views.GetTemplateContent.as_view(),
         name='get_template_content'), # JSON ONLY
    path('<uuid:app_uuid>/template-content-preview/<str:slug>/', views.GetTemplateContentPreview.as_view(), # JSON ONLY
         name='get_template_content_preview'),
    path('<uuid:app_uuid>/template-content-navigation/<str:navigation_type>/<str:language>/', views.GetNavigation.as_view(),
         name='get_template_content_navigation'),
    path('<uuid:app_uuid>/template-content-navigation-preview/<str:navigation_type>/<str:language>/', views.GetNavigationPreview.as_view(),
         name='get_template_content_navigation_preview'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json',])