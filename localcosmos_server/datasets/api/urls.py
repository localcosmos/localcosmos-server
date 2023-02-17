from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('<uuid:app_uuid>/observation-form/', views.CreateObservationForm.as_view(),
        name='api_create_observation_form'),
    path('<uuid:app_uuid>/observation-form/<uuid:observation_form_uuid>/<int:version>/',
        views.RetrieveObservationForm.as_view(), name='api_retrieve_observation_form'),
    path('<uuid:app_uuid>/dataset/', views.CreateDataset.as_view(), name='api_create_dataset'),
    path('<uuid:app_uuid>/dataset/<uuid:uuid>/', views.ManageDataset.as_view(), name='api_manage_dataset'),
    path('<uuid:app_uuid>/datasets/', views.DatasetList.as_view(), name='api_dataset_list'),
    path('<uuid:app_uuid>/dataset-image/', views.CreateDatasetImage.as_view(), name='api_create_dataset_image'),
    path('<uuid:app_uuid>/dataset-image/<int:pk>/', views.DestroyDatasetImage.as_view(), name='api_destroy_dataset_image'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])