from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('<uuid:app_uuid>/observation-form/', views.CreateObservationForm.as_view(),
        name='api_create_observation_form'),
    path('<uuid:app_uuid>/observation-form/<uuid:observation_form_uuid>/<int:version>/',
        views.RetrieveObservationForm.as_view(), name='api_retrieve_observation_form'),
    # dataset
    path('<uuid:app_uuid>/dataset/', views.ListCreateDataset.as_view(), name='api_list_create_dataset'),
    path('<uuid:app_uuid>/dataset/<uuid:uuid>/', views.ManageDataset.as_view(), name='api_manage_dataset'),
    path('<uuid:app_uuid>/dataset/<uuid:uuid>/image/', views.CreateDatasetImage.as_view(),
        name='api_create_dataset_image'),
    path('<uuid:app_uuid>/dataset/<uuid:uuid>/image/<int:pk>/', views.DestroyDatasetImage.as_view(),
        name='api_destroy_dataset_image'),
    # user geometries
    path('<uuid:app_uuid>/user-geometry/', views.CreateListUserGeometry.as_view(),
        name='api_create_list_user_geometry'),
    path('<uuid:app_uuid>/user-geometry/<int:pk>/', views.ManageUserGeometry.as_view(),
        name='api_manage_user_geometry'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])