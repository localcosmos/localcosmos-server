
from collections import OrderedDict
from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry

from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

import json

@extend_schema_field(OpenApiTypes.OBJECT)
class GeoJSONField(serializers.Field):

    def to_representation(self, value):

        if value:

            value.transform(4326)

            geojson = OrderedDict()

            geojson["type"] = "Feature"

            geojson["geometry"] = json.loads(value.geojson)

            geojson["geometry"]["crs"] = {
                "type": "name",
                "properties": {  
                    "name": "EPSG:{0}".format(value.srid)
                }
            }
            
            return dict(geojson)

        return value

    def to_internal_value(self, data):
        geojson = json.dumps(data['geometry'])
        srid_str = data['geometry']['crs']['properties']['name']
        srid = int(srid_str.split(':')[-1])
        geos_geometry = GEOSGeometry(geojson, srid=srid)
        return geos_geometry