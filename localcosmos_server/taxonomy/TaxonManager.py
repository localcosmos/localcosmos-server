from django.db.models import Q

from django.utils.translation import gettext_lazy as _

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon, ModelWithTaxon

from localcosmos_server.models import TaxonomicRestriction
from localcosmos_server.datasets.models import Dataset, DatasetValidationRoutine
from localcosmos_server.models import ServerImageStore

from localcosmos_server.utils import get_subclasses, get_content_instance_app

SUPPORTED_SWAP_MODELS = []
# Datasets are Documents and cannot be touched by generic operations like this
UNSUPPORTED_SWAP_MODELS = [Dataset, DatasetValidationRoutine, TaxonomicRestriction, ServerImageStore]

SWAPPABILITY_CHECK_STATIC_FIELDS = {
    'Dataset': [],
    'DatasetValidationRoutine': ['app'],
    'TaxonomicRestriction': ['content_type', 'object_id'],
    'ServerImageStore': [],
}

class TaxonManager:
    
    supported_swap_models = SUPPORTED_SWAP_MODELS
    unsupported_swap_models = UNSUPPORTED_SWAP_MODELS
    
    swappability_check_static_fields = SWAPPABILITY_CHECK_STATIC_FIELDS
    
    def __init__(self, app):
        self.app = app
        
    def get_taxon_models(self):
        
        required_taxa_classes = get_subclasses(ModelWithRequiredTaxon)
        optional_taxa_classes = get_subclasses(ModelWithTaxon)
        
        taxon_models = required_taxa_classes + optional_taxa_classes
        
        return taxon_models
    
    
    '''
        currently only supports scientific names
        searches for a taxon across all valid taxon models
    '''
    def get_base_occurrence_query(self, model, lazy_taxon):
        
        taxon_source = lazy_taxon.taxon_source
        taxon_latname = lazy_taxon.taxon_latname
        taxon_author = lazy_taxon.taxon_author
        
        occurrence_qry = model.objects.filter(taxon_source=taxon_source, taxon_latname=taxon_latname)
            
        if taxon_author:
            occurrence_qry = occurrence_qry.filter(taxon_author=taxon_author)
        else:
            # use Django Q to query for null or empty author
            occurrence_qry = occurrence_qry.filter(Q(taxon_author__isnull=True) | Q(taxon_author=''))
        
        return occurrence_qry
        
        
    def get_taxon_occurrences(self, lazy_taxon):
        
        models = self.get_taxon_models()
        
        occurrences = []
        
        for model in models:
            
            occurrence_qry = self.get_base_occurrence_query(model, lazy_taxon)
                
            # depending on the model class name, execude _get_..._occurrence_entry
            # to get the correct occurrence entry
            method_name = f'_get_{model.__name__}_occurrences'
            if hasattr(self, method_name):
                model_occurrences = getattr(self, method_name)(occurrence_qry, lazy_taxon)
                
                if model_occurrences:
                    
                    occurrences.append({
                        'model': model,
                        'occurrences' : model_occurrences,
                    })
            else:
                # raise an error
                raise NotImplementedError(f'Method {method_name} not implemented for model {model.__name__}')
            
        return occurrences
    
    '''
        methods for localcosmos_server taxonomic models
    '''
    
    # has a field app_uuid
    def _get_Dataset_occurrences(self, occurrence_qry, lazy_taxon):
        occurrence_qry = occurrence_qry.filter(app_uuid=self.app.uuid)
        return occurrence_qry
    
    # has a OnetoOne field to App
    def _get_DatasetValidationRoutine_occurrences(self, occurrence_qry, lazy_taxon):
        occurrence_qry = occurrence_qry.filter(app=self.app)
        return occurrence_qry
    
    # has no reference to App
    # currently, only TemplateContent and DatasetValidationRoutine can have
    # a taxonomic restriction
    def _get_TaxonomicRestriction_occurrences(self, occurrence_qry, lazy_taxon):
        matching_occurrences = []
        for occurrence in occurrence_qry:
            content_instance = occurrence.content
            
            content_instance_app = get_content_instance_app(content_instance)
            if content_instance_app == self.app:
                matching_occurrences.append(occurrence)
        return matching_occurrences
    
    
    # has no reference to App, currently unsupported
    def _get_ServerImageStore_occurrences(self, occurrence_qry, lazy_taxon):
        return []
    
    
    def perform_swap(self, model, lazy_taxon, new_lazy_taxon):
        
        occurrences = model.objects.filter(taxon_source=lazy_taxon.taxon_source,taxon_latname=lazy_taxon.taxon_latname)
                
        # model specific query
        query_method = f'_get_{model.__name__}_occurrences'
        if hasattr(self, query_method):
            occurrences = getattr(self, query_method)(occurrences, lazy_taxon)
        else:
            # raise an error
            raise NotImplementedError(f'Method {query_method} not implemented for model {model.__name__}')
        
        for occurrence in occurrences:
            
            is_swappable = self.check_swappability([occurrence], new_lazy_taxon)
            
            if is_swappable == True:
                occurrence.set_taxon(new_lazy_taxon)
                occurrence.save()
        
    # swap a taxon across all models
    def swap_taxon(self, lazy_taxon, new_lazy_taxon):
        
        models = self.get_taxon_models()
        
        for model in models:
            if model in self.supported_swap_models:
                
                custom_swap_method = '_swap_taxon_{0}'.format(model.__name__)

                if hasattr(self, custom_swap_method):
                    getattr(self, custom_swap_method)(lazy_taxon, new_lazy_taxon)
                else:
                    self.perform_swap(model, lazy_taxon, new_lazy_taxon)

            # if the model is not supported, skip it
            elif model in self.unsupported_swap_models:
                #print(f'Skipping model {model.__name__} for taxon swap')
                continue
            else:
                # raise an error
                raise NotImplementedError(f'Model {model.__name__} not supported for taxon swap')
            
    
    def _get_verbose_entry(self, model, occurrences, verbose_model_name, verbose_occurrences):
        
        verbose_entry = {
            'model': model,
            'occurrences': occurrences,
            'verbose_model_name': verbose_model_name,
            'verbose_occurrences': verbose_occurrences,
        }
        
        return verbose_entry
    
    def _get_Dataset_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [
            _('occurs in %(count)s datasets') % {'count': len(occurrences)}
        ]
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        
        return [verbose_entry]
    
    
    def _get_DatasetValidationRoutine_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [
                _('occurs in %(count)s validation routines') % {'count': len(occurrences)}
        ]
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        
        return [verbose_entry]
    
    
    def _get_TaxonomicRestriction_occurrences_verbose(self, occurrences_entry):
        
        verbose_occurrences_entries = []
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        for occurrence in occurrences:
            
            verbose_occurrences = []
            content_instance = occurrence.content

            verbose_model_name = str(content_instance._meta.verbose_name)
            verbose_occurrences = [_('acts as a taxonomic restriction of %(instance)s') % {
                'instance': str(content_instance)}
            ]
            
            verbose_entry = self._get_verbose_entry(model, [occurrence], verbose_model_name, verbose_occurrences)
            
            verbose_occurrences_entries.append(verbose_entry)
        
        return verbose_occurrences_entries    
    
    def get_verbose_occurrences(self, lazy_taxon):
        
        occurrences = self.get_taxon_occurrences(lazy_taxon)
        verbose_occurrences = []
        
        for occurrences_entry in occurrences:
            
            model = occurrences_entry['model']
            model_name = model.__name__
                
            verbose_occurrences_method = f'_get_{model_name}_occurrences_verbose'
            if hasattr(self, verbose_occurrences_method):
                verbose_occurrences_list = getattr(self, verbose_occurrences_method)(occurrences_entry)
                
                if verbose_occurrences_list:
                    verbose_occurrences.extend(verbose_occurrences_list)
            else:
                # raise an error
                raise NotImplementedError(f'Method {verbose_occurrences_method} not implemented for model {model_name}')
            
        return verbose_occurrences
    
    def _resolve_related_field(self, instance, field_path):
        """
        Resolves a related field value for a given instance and field path.
        Supports Django's double-underscore syntax for related lookups.
        """
        parts = field_path.split('__')
        value = instance
        for part in parts:
            value = getattr(value, part, None)
            if value is None:
                break
        return value

    def check_swappability(self, occurrences, to_taxon):
        
        for occurrence in occurrences:
        
            model = occurrence.__class__
            model_name = model.__name__
            
            # check swappability parameters
            static_fields = self.swappability_check_static_fields[model_name]
            
            lookup_kwargs = {
                'taxon_source': to_taxon.taxon_source,
                'taxon_latname': to_taxon.taxon_latname,
                'taxon_author': to_taxon.taxon_author,
            }
            
            for field in static_fields:
                if '__' in field:
                    # Handle double-underscore lookups directly
                    lookup_kwargs[field] = self._resolve_related_field(occurrence, field)
                else:
                    # Handle direct fields
                    lookup_kwargs[field] = getattr(occurrence, field, None)
            
            exists = model.objects.filter(**lookup_kwargs).exists()
            if exists:
                return False
            
        return True
    
    
    def get_swap_analysis(self, from_taxon, to_taxon):
        
        occurrences_entries = self.get_verbose_occurrences(from_taxon)
        
        swap_analysis = []
        
        for occurrence_entry in occurrences_entries:
            model = occurrence_entry['model']
            occurrences = occurrence_entry['occurrences']
            
            swappable = False
            
            # check if the model is supported for swapping
            if model in self.supported_swap_models:
                
                # check if the taxon can be swapped
                swappable = self.check_swappability(occurrences, to_taxon)
                
            new_entry = occurrence_entry.copy()
            new_entry['is_swappable'] = swappable
            
            swap_analysis.append(new_entry)
        
        return swap_analysis
        