
from collections import OrderedDict
from rest_framework import serializers
from django.core.serializers import serialize

# WIP
class GeoJSONField(serializers.Field):

    def to_representation(self, value):

        # prepare OrderedDict geojson structure
        geojson = OrderedDict()

        geojson["type"] = "Feature"

        geojson["geometry"] = value.geojson
        
        return geojson

    def to_internal_value(self, data):
        data = data.strip('rgb(').rstrip(')')
        red, green, blue = [int(col) for col in data.split(',')]
        return (red, green, blue)