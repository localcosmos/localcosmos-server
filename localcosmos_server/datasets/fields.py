# import all available fields
from django import forms
from django.forms.fields import *
from localcosmos_server.taxonomy.fields import *
from localcosmos_server.utils import cron_from_datetime

import json

from .widgets import (JSONWidget, SelectDateTimeWidget, MobilePositionInput, CameraAndAlbumWidget,
                        PointOrAreaInput)


class JSONField(forms.MultiValueField):

    widget = JSONWidget

    def __init__(self, *args, **kwargs):
        
        fields = (
            forms.CharField(),
            forms.CharField(),
        )
        super().__init__(fields, **kwargs)
        

    def compress(self, data_list):

        """
        Return a single value for the given list of values. The values can be
        assumed to be valid.

        For example, if this MultiValueField was instantiated with
        fields=(DateField(), TimeField()), this might return a datetime
        object created by combining the date and time in data_list.
        """

        if data_list:
            return json.loads(data_list[1])

        return None


'''
    Fields for Taxonomic, Geographic and Temporal Reference Fields
'''
class DateTimeJSONField(forms.DateTimeField):

    widget = SelectDateTimeWidget

    '''
        create a valid Temporal JSON
    '''
    def to_python(self, value):
        if value:
            datetime_object = super().to_python(value)
            return cron_from_datetime(datetime_object)
        
        return None



class PointJSONField(JSONField):
    
    widget = MobilePositionInput

    def compress(self, data_list):

        if data_list:
            return json.loads(data_list[1])

        return None


class GeoJSONField(JSONField):
    
    widget = PointOrAreaInput

    def compress(self, data_list):

        if data_list:
            return json.loads(data_list[1])

        return None



class PictureField(forms.ImageField):

    widget = CameraAndAlbumWidget


