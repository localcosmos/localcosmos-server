from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

app_name = 'google_cloud_api'

urlpatterns = [
    # app unspecific
    path('app/<uuid:app_uuid>/image-recognition/', views.ImageRecognition.as_view()),

]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json',])
