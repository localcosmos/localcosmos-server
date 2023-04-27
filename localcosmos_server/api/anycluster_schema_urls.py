from django.urls import path
from . import views

from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
     path('grid/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaGridCluster.as_view()), name='schema_grid_cluster'),
     path('kmeans/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaKmeansCluster.as_view()), name='schema_kmeans_cluster'),
     path('get-kmeans-cluster-content/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaGetClusterContent.as_view()),
          name='schema_get_kmeans_cluster_content'),
     path('get-area-content/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaGetAreaContent.as_view(),),
          name='schema_get_area_content'),
     path('get-dataset-content/<int:zoom>/<int:grid_size>/<int:dataset_id>/',
          csrf_exempt(views.SchemaGetDatasetContent.as_view(),), name='schema_get_dataset_content'),
]

