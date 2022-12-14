from django.urls import include, path
from . import views
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = [
    path('template-content/<str:slug>/', views.GetTemplateContent.as_view(), name='get_template_content'), # JSON ONLY
    path('template-content-preview/<str:slug>/', views.GetTemplateContentPreview.as_view(), # JSON ONLY
         name='get_template_content_preview'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json',])