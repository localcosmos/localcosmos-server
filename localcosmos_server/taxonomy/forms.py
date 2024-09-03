from django import forms
from django.utils.translation import gettext_lazy as _

'''
    A form to search app taxa from disk or from db, depending on the taxon_search_url
'''
from .fields import TaxonField
from .widgets import TaxonAutocompleteWidget
from .lazy import LazyAppTaxon

class AddSingleTaxonForm(forms.Form):
    
    lazy_taxon_class = LazyAppTaxon

    def __init__(self, *args, **kwargs):
        
        lazy_taxon_class = kwargs.pop('lazy_taxon_class', self.lazy_taxon_class)

        #required: taxon_search_url
        taxon_search_url = kwargs.pop('taxon_search_url', None)

        if taxon_search_url == None:
            raise ValueError('taxon_search_url is required for AddSingleTaxonForm')

        # fixed taxon source or not
        fixed_taxon_source = kwargs.pop('fixed_taxon_source', None)
        
        descendants_choice = kwargs.pop('descendants_choice', False)
        

        super().__init__(*args, **kwargs)

        # the field_kwargs are also passed to the widget
        field_kwargs = {
            'taxon_search_url' : taxon_search_url,
            'descendants_choice' : descendants_choice,
            'fixed_taxon_source' : fixed_taxon_source,
            'widget_attrs' : {},
            'lazy_taxon_class': lazy_taxon_class,
        }

        self.fields['taxon'] = TaxonField(label=_('Taxon'), required=True, **field_kwargs)


from localcosmos_server.models import TAXONOMIC_RESTRICTION_TYPES
class TypedTaxonomicRestrictionForm(AddSingleTaxonForm):
    restriction_type = forms.ChoiceField(choices=TAXONOMIC_RESTRICTION_TYPES, initial='exists')
