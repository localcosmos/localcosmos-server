from django import forms

from localcosmos_server.geography.models import PolygonCategory, GeographyPolygon

from django.utils.translation import gettext as _

import json

class PolygonCategoryForm(forms.ModelForm):
    class Meta:
        model = PolygonCategory
        fields = (
            'name',
        )
        help_texts = {
            'name': _('Name of this category, e.g. "Parks", "Protected areas", "Biomes".'),
        }
        


class PolygonForm(forms.Form):

    polygon = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=255, required=False)
    code = forms.CharField(max_length=255, required=False)

    def clean_polygon(self):

        geojson_str = self.cleaned_data['polygon']

        if len(geojson_str) > 0:

            try:
                geojson = json.loads(geojson_str)
            except:
                del self.cleaned_data['polygon']
                raise forms.ValidationError(_('Invalid geometry'))
        
        return geojson_str
