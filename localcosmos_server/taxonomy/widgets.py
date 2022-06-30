from django.conf import settings
from django.forms.widgets import MultiWidget, HiddenInput, CheckboxInput
from django.urls import reverse

# search across all taxonomy databases
# fixed source just needs to change the template
class TaxonAutocompleteWidget(MultiWidget):

    template_name = 'localcosmos_server/widgets/taxonomy/taxon_autocomplete_widget.html'

    def __init__(self, **kwargs):

        attrs = kwargs.get('attrs', {})
        attrs['required'] = True

        # set after form.init
        self.taxon_search_url = kwargs['taxon_search_url']
        
        self.dispatch_change_event = kwargs.get('dispatch_change_event', False)

        self.descendants_choice = kwargs.pop('descendants_choice', False)
        self.fixed_taxon_source = kwargs.pop('fixed_taxon_source', None)
        self.display_language_field = kwargs.pop('display_language_field', True)
        
        widgets = [
            HiddenInput(attrs=attrs), # taxon_source
            HiddenInput(attrs=attrs), # taxon_latname
            HiddenInput(attrs=attrs), # taxon_author
            HiddenInput(attrs=attrs), # name_uuid
            HiddenInput(attrs=attrs), # taxon_nuid
        ]

        if self.descendants_choice == True:
            choice_attrs = attrs.copy()
            choice_attrs.pop('required')
            widgets.append(CheckboxInput(attrs=attrs))

        widgets = tuple(widgets)

        super().__init__(widgets, attrs)



    @property
    def is_hidden(self):
        return False
    

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        if settings.LOCALCOSMOS_PRIVATE == True:
            taxon_source_choices = []
        else:
            taxon_source_choices = settings.TAXONOMY_DATABASES

        context.update({
            'taxon_source_choices' : taxon_source_choices,
            'taxon_search_url' : self.taxon_search_url,
            'fixed_taxon_source' : self.fixed_taxon_source,
            'dispatch_change_event' : self.dispatch_change_event,
            'descendants_choice' : self.descendants_choice,
            'display_language_field' : self.display_language_field,
        })

        return context


    def decompress(self, lazy_taxon):

        if lazy_taxon:
            data_list = [lazy_taxon.taxon_source, lazy_taxon.taxon_latname, lazy_taxon.taxon_author,
                         str(lazy_taxon.name_uuid), lazy_taxon.taxon_nuid]
            return data_list

        return []
