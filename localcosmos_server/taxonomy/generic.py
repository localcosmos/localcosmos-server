from django.db import models
from django.utils.translation import gettext_lazy as _

from .lazy import LazyAppTaxon

'''
    Model Mixins for Adding Taxa to models
    - loose link to any taxonomic source, defined by
    -- taxon_latname
    -- taxon_author
    -- taxon_source
    -- taxon_nuid
    -- name_uuid
'''
class ModelWithTaxonCommon(models.Model):

    LazyTaxonClass = LazyAppTaxon

    def __init__(self, *args, **kwargs):

        self.taxon = None
        
        # a lazy taxon instance
        lazy_taxon = kwargs.pop('taxon', None)
        
        super().__init__(*args, **kwargs)

        if lazy_taxon:
            self.set_taxon(lazy_taxon)

        elif self.pk:

            if self.taxon_latname and self.taxon_source and self.taxon_nuid and self.name_uuid:
                lazy_taxon = self.LazyTaxonClass(instance=self)
                self.set_taxon(lazy_taxon)

    def load_taxon(self):
        if self.taxon_latname:
            taxon = self.get_taxon()
    
    '''
    get the LazyTaxon instance
    '''
    def get_taxon(self):

        if self.taxon is not None:
            return self.taxon
        
        else:
            # load the taxon instance from the source

            if self.taxon_nuid and self.taxon_latname and self.taxon_source:

                lazy_taxon_kwargs = {
                    'name_uuid' : str(self.name_uuid),
                    'taxon_nuid' : self.taxon_nuid,
                    'taxon_latname' : self.taxon_latname,
                    'taxon_author' : self.taxon_author,
                    'taxon_source' : self.taxon_source,
                    'taxon_include_descendants' : self.taxon_include_descendants,
                }
                lazy_taxon = LazyAppTaxon(**lazy_taxon_kwargs)
                self.set_taxon(lazy_taxon)
                
        return self.taxon


    def set_taxon_parameters(self, lazy_taxon):

        self.name_uuid = str(lazy_taxon.name_uuid)
        self.taxon_nuid = lazy_taxon.taxon_nuid
        self.taxon_latname = lazy_taxon.taxon_latname
        self.taxon_author = lazy_taxon.taxon_author
        self.taxon_source = lazy_taxon.taxon_source
        self.taxon_include_descendants = lazy_taxon.taxon_include_descendants


    def set_taxon(self, lazy_taxon):

        # allow setting with LazyTaxon or LazyAppTaxon
        
        self.set_taxon_parameters(lazy_taxon)

        # the lazy taxon, make sure it is the right LazyTaxonClass
        lazy_taxon_kwargs = {
            'taxon_latname' : lazy_taxon.taxon_latname,
            'taxon_author' : lazy_taxon.taxon_author,
            'taxon_source' : lazy_taxon.taxon_source,
            'taxon_include_descendants' : lazy_taxon.taxon_include_descendants,
            'name_uuid' : str(lazy_taxon.name_uuid),
            'taxon_nuid' : lazy_taxon.taxon_nuid,
        }
        
        self.taxon = self.LazyTaxonClass(**lazy_taxon_kwargs)


    def remove_taxon(self):
        self.name_uuid = None
        self.taxon_nuid = None
        self.taxon_latname = None
        self.taxon_author = None
        self.taxon_source = None
        self.taxon_include_descendants = None


    def vernacular(self, language=None):
        if not self.taxon:
            self.get_taxon()

        if self.taxon:
            vernacular = self.taxon.vernacular(language)

            if vernacular:
                return vernacular

        return ''
        
    # returns a string
    def taxon_verbose(self, language):
        
        if not self.taxon:
            self.get_taxon()

        if self.taxon:
            vernacular = self.taxon.vernacular(language)

            if vernacular:
                return '{0} ({1})'.format(vernacular, self.taxon_latname)

            return self.taxon_latname
            
        return 'no taxon assigned'


    def save(self, *args, **kwargs):
        
        if self.taxon is not None:
            self.set_taxon(self.taxon)


        # make sure there is no taxon saved without all parameters set correctly
        taxon_required_fields = set(['taxon_source', 'taxon_nuid', 'taxon_latname', 'name_uuid'])

        for field_name in taxon_required_fields:

            if getattr(self, field_name, None) is not None:

                for required_field_name in taxon_required_fields:

                    required_field_value = getattr(self, required_field_name, None)

                    if required_field_value is None or len(required_field_value) == 0:
                        raise ValueError('If you add a taxon to a model, the field "{0}" is required'.format(
                            required_field_name))

                break

        super().save(*args, **kwargs)


    '''
    updating the taxon of ModelWithTaxon
    '''
    # only callable by LazyTaxon, not LazyAppTaxon
    def update_taxon(self):
        lazy_taxon = self.get_taxon()
        if lazy_taxon:
            if lazy_taxon.exists_in_tree():
                tree_instance = lazy_taxon.tree_instance()

                if str(tree_instance.name_uuid) != str(self.name_uuid) or tree_instance.taxon_nuid != self.taxon_nuid:

                    new_lazy_taxon = LazyAppTaxon(instance=tree_instance)
                    new_lazy_taxon.taxon_include_descendants = self.taxon_include_descendants
                    
                    self.set_taxon(new_lazy_taxon)
                    self.save()

            elif lazy_taxon.exists_as_synonym():

                synonym_instance = lazy_taxon.synonym_instance()
                tree_instance = synonym_instance.taxon
                
                new_lazy_taxon = LazyAppTaxon(instance=tree_instance)
                new_lazy_taxon.taxon_include_descendants = self.taxon_include_descendants
                    
                self.set_taxon(new_lazy_taxon)
                self.save()

        
    class Meta:
        abstract = True
    
    

'''
    ModelWithTaxon
    - taxon is optional
    - if a taxon is set, all parameters are required
'''
class ModelWithTaxon(ModelWithTaxonCommon):

    taxon_latname = models.CharField(max_length=255, null=True)
    taxon_author = models.CharField(max_length=255, null=True)
    taxon_source = models.CharField(max_length=255, null=True)

    taxon_include_descendants = models.BooleanField(default=False)

    taxon_nuid = models.CharField(max_length=255, null=True)
    name_uuid = models.UUIDField(null=True)

    

    def remove_taxon(self):
        self.taxon = None
        self.taxon_latname = None
        self.taxon_author = None
        self.taxon_source = None

        self.taxon_nuid = None
        self.name_uuid = None

        self.save()


    class Meta:
        abstract = True
        
        
class ModelWithRequiredTaxon(ModelWithTaxonCommon):
    
    taxon_latname = models.CharField(max_length=255)
    taxon_author = models.CharField(max_length=255, null=True) # some higher taxa have no author
    taxon_source = models.CharField(max_length=255)

    taxon_include_descendants = models.BooleanField(default=False)

    taxon_nuid = models.CharField(max_length=255)
    name_uuid = models.UUIDField()

    class Meta:
        abstract = True
