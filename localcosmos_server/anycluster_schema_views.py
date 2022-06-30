from django.conf import settings
from django.http import HttpResponse
from django.db.models import ForeignKey
from django.core import serializers

from anycluster.views import GridCluster, KmeansCluster, GetClusterContent, GetAreaContent
from anycluster.MapClusterer import MapClusterer

import json, uuid

def get_init_kwargs(request):
    kwargs = {}
    if settings.LOCALCOSMOS_PRIVATE == False:
        kwargs['schema_name'] = request.tenant.schema_name
    return kwargs

class SchemaGridCluster(GridCluster):

    def get_clusterer(self, request, zoom, grid_size, **kwargs):
        init_kwargs = get_init_kwargs(request)
        clusterer = MapClusterer(request, zoom, grid_size, **init_kwargs)
        return clusterer

class SchemaKmeansCluster(KmeansCluster):

    def get_clusterer(self, request, zoom, grid_size, **kwargs):
        init_kwargs = get_init_kwargs(request)
        clusterer = MapClusterer(request, zoom, grid_size, **init_kwargs)
        return clusterer


'''
    allow json responses for the app clients on the cluster content
    - datasets need to be serialized
    - ForeignKeys are currently unsupported by anycluster (possible bug in django)
'''

class SchemaGetClusterContent(GetClusterContent):

    def get_clusterer(self, request, zoom, grid_size, **kwargs):
        init_kwargs = get_init_kwargs(request)
        clusterer = MapClusterer(request, zoom, grid_size, **init_kwargs)
        return clusterer
    

class SchemaGetAreaContent(GetAreaContent):

    def get_clusterer(self, request, zoom, grid_size, **kwargs):
        init_kwargs = get_init_kwargs(request)
        clusterer = MapClusterer(request, zoom, grid_size, **init_kwargs)
        return clusterer


