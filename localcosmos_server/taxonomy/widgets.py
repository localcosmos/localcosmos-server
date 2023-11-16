from django.conf import settings
from django.forms.widgets import MultiWidget, HiddenInput, CheckboxInput
from localcosmos_server.taxonomy.lazy import LazyAppTaxon

import json

# search across all taxonomy databases
# fixed source just needs to change the template
class ListToLazyTaxon:

    def get_taxon_kwargs(self, data_list):

        if len(data_list) >= 4:

            taxon_kwargs = {
                'taxon_source' : data_list[0],
                'taxon_latname' : data_list[1],
                'taxon_author' : data_list[2],
                'name_uuid' : data_list[3],
                'taxon_nuid' : data_list[4],
            }

            return taxon_kwargs
        return None

    def get_lazy_taxon(self, data_list):

        taxon_kwargs = self.get_taxon_kwargs(data_list)

        if taxon_kwargs:
            lazy_taxon = self.lazy_taxon_class(**taxon_kwargs)

            return lazy_taxon

        return None


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


class FixedTaxonWidget(TaxonAutocompleteWidget):
    template_name = 'localcosmos_server/widgets/taxonomy/fixed_taxon_widget.html'


def get_choices_from_taxonomic_restrictions(taxonomic_restrictions):
    choices = []

    for taxonomic_restriction in taxonomic_restrictions:

        if isinstance(taxonomic_restriction, dict):
            choices.append(
                (taxonomic_restriction['nameUuid'], taxonomic_restriction['taxonLatname'])
            )
        else:
            choices.append(
                (taxonomic_restriction.name_uuid, taxonomic_restriction.taxon_latname)
            )
    
    return choices


def get_taxon_map_from_taxonomic_restrictions(taxonomic_restrictions):
    taxon_map = {}

    for taxonomic_restriction in taxonomic_restrictions:

        if isinstance(taxonomic_restriction, dict):
            taxon_map[taxonomic_restriction['nameUuid']] = {
                'taxon_source': taxonomic_restriction['taxonSource'],
                'taxon_latname': taxonomic_restriction['taxonLatname'],
                'taxon_author': taxonomic_restriction['taxonAuthor'],
                'name_uuid': taxonomic_restriction['nameUuid'],
                'taxon_nuid': taxonomic_restriction['taxonNuid'],
            }

        else:
            taxon_map[taxonomic_restriction.name_uuid] = {
                'taxon_source': taxonomic_restriction.taxon_source,
                'taxon_latname': taxonomic_restriction.taxon_latname,
                'taxon_author': taxonomic_restriction.taxon_author,
                'name_uuid': taxonomic_restriction.name_uuid,
                'taxon_nuid': taxonomic_restriction.taxon_nuid,
            }
    
    return taxon_map


class SelectTaxonWidget(ListToLazyTaxon, MultiWidget):
    template_name = 'localcosmos_server/widgets/taxonomy/select_taxon_widget.html'
    lazy_taxon_class = LazyAppTaxon

    def __init__(self, **kwargs):

        self.choices = kwargs['choices']
        self.taxon_map = kwargs['taxon_map']

        attrs = kwargs.get('attrs', {})
        attrs['required'] = True

        widgets = [
            HiddenInput(attrs=attrs), # taxon_source
            HiddenInput(attrs=attrs), # taxon_latname
            HiddenInput(attrs=attrs), # taxon_author
            HiddenInput(attrs=attrs), # name_uuid
            HiddenInput(attrs=attrs), # taxon_nuid
        ]

        widgets = tuple(widgets)

        super().__init__(widgets, attrs)


    @property
    def is_hidden(self):
        return False
    

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        context['choices'] = self.choices
        context['taxon_map'] = json.dumps(self.taxon_map);

        return context
    
    
    def decompress(self, lazy_taxon):

        if lazy_taxon:
            data_list = [lazy_taxon.taxon_source, lazy_taxon.taxon_latname, lazy_taxon.taxon_author,
                         str(lazy_taxon.name_uuid), lazy_taxon.taxon_nuid]
            return data_list

        return []
    
    
    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        if value == "" or value is None:
            return None
        # LazyAppTaxon
        if isinstance(value, list):
            value = self.get_lazy_taxon(value)
        return value

