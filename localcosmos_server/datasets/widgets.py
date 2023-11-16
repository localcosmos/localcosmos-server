from django.contrib.gis import forms
from django.forms.widgets import *
from django.utils.translation import gettext_lazy as _

from localcosmos_server.taxonomy.widgets import (TaxonAutocompleteWidget as BackboneTaxonAutocompleteWidget,
                                                 SelectTaxonWidget)

import json


'''
    JSONWidget consist of one hidden TextInput (the json)
    and a verbose TextInput for interacting and displaying human-readable data
'''
class JSONWidget(forms.MultiWidget):

    def __init__(self, attrs=None):

        widgets = (
            forms.TextInput,
            forms.HiddenInput,
        )

        super().__init__(widgets, attrs=attrs)

    def verbose_value(self, value):
        raise NotImplementedError("JSONWidgets need to implement verbose_value")

    def value_to_json(self, value):
        raise NotImplementedError("JSONWidgets need to implement value_to_json")

    # value is eg datetime with timezone
    def decompress(self, value):
        """
        Return a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """

        if value:
            return [self.verbose_value(value), self.value_to_json(value)]
		
        return [None, None]


    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        if value and len(value) == 2:
            return [value[0], json.dumps(value[1])]
        
        return None
    

class MobileNumberInput(forms.NumberInput):

    template_name = 'datasets/widgets/mobile_number_input.html'


# data is geojson
class MobilePositionInput(JSONWidget):

    template_name = 'datasets/widgets/mobile_position_input.html'

    def value_to_json(self, value):
        if type(value) == str:
            return json.loads(value)
        return value

    def verbose_value(self, value):
        coords = value['geometry']['coordinates']
        verbose_position = '{0} {1} ({2}m)'.format(coords[0], coords[1], value['properties']['accuracy'])
        return verbose_position


    def get_context(self, name, value, attrs):

        if value and value != [None, None]:

            if isinstance(value, list):
                value = [value[0], self.value_to_json(value[1])]
            else:
                value = self.decompress(value)

        context = super().get_context(name, value, attrs)

        return context


class PointOrAreaInput(JSONWidget):
    template_name = 'datasets/widgets/point_or_area_input.html'

    def verbose_value(self, value):
        return _('Point or Area')
    
    def value_to_json(self, value):
        if type(value) == str:
            return json.loads(value)
        return value

        
class SelectDateTimeWidget(forms.DateTimeInput):
    template_name = 'datasets/widgets/select_datetime_widget.html'


class CameraAndAlbumWidget(forms.FileInput):
    template_name = 'datasets/widgets/picture_widget.html'
