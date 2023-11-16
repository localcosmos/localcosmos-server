from django import forms
from django.utils.translation import gettext_lazy as _

from localcosmos_server.taxonomy.lazy import LazyAppTaxon

from localcosmos_server.taxonomy.widgets import (TaxonAutocompleteWidget, SelectTaxonWidget, ListToLazyTaxon)

'''
    A field that returns a LazyTaxon instance
'''
class LazyTaxonField(ListToLazyTaxon):

    def compress(self, data_list):
        return self.get_lazy_taxon(data_list)
    


class TaxonField(LazyTaxonField, forms.MultiValueField):

    widget = TaxonAutocompleteWidget
    lazy_taxon_class = LazyAppTaxon

    def __init__(self, *args, **kwargs):

        self.lazy_taxon_class = kwargs.pop('lazy_taxon_class', self.lazy_taxon_class)

        taxon_search_url = kwargs.pop('taxon_search_url')
        
        descendants_choice = kwargs.pop('descendants_choice', False)
        fixed_taxon_source = kwargs.pop('fixed_taxon_source', None)
        display_language_field = kwargs.pop('display_language_field', True)

        widget_kwargs = {
            'taxon_search_url' : taxon_search_url,
            'descendants_choice' : descendants_choice,
            'fixed_taxon_source' : fixed_taxon_source,
            'display_language_field' : display_language_field,
            'attrs' : kwargs.pop('widget_attrs', {}),
        }

        self.widget = self.widget(**widget_kwargs)
        
        fields = [
            forms.CharField(), # taxon_source
            forms.CharField(), # taxon_latname
            forms.CharField(required=False), # taxon_author
            forms.CharField(), # name_uuid
            forms.CharField(), # taxon_nuid
        ]

        if descendants_choice == True:
            fields.append(forms.BooleanField(required=False, label=_('Include descendants')))

        fields = tuple(fields)

        super().__init__(fields, *args, require_all_fields=False, **kwargs)


    def get_lazy_taxon(self, data_list):

        taxon_kwargs = self.get_taxon_kwargs(data_list)

        if taxon_kwargs:
            if len(data_list) == 6:
                taxon_kwargs['taxon_include_descendants'] = data_list[5]

            lazy_taxon = self.lazy_taxon_class(**taxon_kwargs)

            return lazy_taxon

        return None



class SelectTaxonField(LazyTaxonField, forms.MultiValueField):
    
    widget = SelectTaxonWidget
    lazy_taxon_class = LazyAppTaxon

    def __init__(self, *args, **kwargs):

        choices = kwargs.pop('choices')
        taxon_map = kwargs.pop('taxon_map')

        widget_kwargs = {
            'choices' : choices,
            'taxon_map': taxon_map,
            'attrs' : kwargs.pop('widget_attrs', {}),
        }

        self.widget = self.widget(**widget_kwargs)
        
        fields = [
            forms.CharField(), # taxon_source
            forms.CharField(), # taxon_latname
            forms.CharField(required=False), # taxon_author
            forms.CharField(), # name_uuid
            forms.CharField(), # taxon_nuid
        ]

        super().__init__(fields, *args, require_all_fields=True, **kwargs)

