from django.conf.urls import url
from django.urls import path
from . import anycluster_schema_views as views

from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('grid/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaGridCluster.as_view()), name='grid_cluster'),
    path('kmeans/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaKmeansCluster.as_view()), name='kmeans_cluster'),
    path('getClusterContent/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaGetClusterContent.as_view()),
         name='get_cluster_content'),
    path('getAreaContent/<int:zoom>/<int:grid_size>/', csrf_exempt(views.SchemaGetAreaContent.as_view()),
         name='get_area_content'),
]
