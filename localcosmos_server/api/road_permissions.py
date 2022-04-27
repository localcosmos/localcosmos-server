from rest_framework import permissions

from django.conf import settings

from django_road import permissions as road_permissions
from .permissions import CanCreateDataset

import os, json


ROAD_MODEL_PERMISSIONS = {
    'LocalcosmosUser' : {
        'first' : [road_permissions.OwnerOnly],
        'default' : [road_permissions.OwnerOnly],
        'create' : [road_permissions.PermissionDenied], # uses separate api
        'fetch' : [road_permissions.PermissionDenied], # do not allow this
        'count' : [road_permissions.PermissionDenied], # do not allow this
    },
    'Dataset' : {
        'get' : [],
        'filter' : [],
        'first' :[],
        'fetch' :[],
        'count' : [],
        'delete' : [road_permissions.OwnerOnly],
        'update' : [road_permissions.OwnerOnly],
        'insert' : [CanCreateDataset], # app specific permission needed
    },
    'DatasetImages' : {
        'get' : [],
        'filter' : [],
        'first' :[],
        'fetch' :[],
        'count' : [],
        'delete' : [road_permissions.OwnerOnly],
        'update' : [road_permissions.OwnerOnly],
        'insert' : [CanCreateDataset], # app specific permission needed
    }
}
