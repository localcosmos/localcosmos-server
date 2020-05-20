from django.db import models
from django.utils.translation import gettext_lazy as _

from .lazy import LazyAppTaxon

'''
    Model Mixins for Adding Taxa to models
    - loose link to any taxonomic source, defined by
    -- taxon_uuid
    -- taxon_nuid
    -- taxon_latname
    -- taxon_source
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
            if self.taxon_uuid:
                lazy_taxon = self.LazyTaxonClass(instance=self)
                self.set_taxon(lazy_taxon)

    def load_taxon(self):
        if self.taxon_uuid:
            taxon = self.get_taxon()
    
    '''
    get the LazyTaxon instance
    '''
    def get_taxon(self):

        if self.taxon is not None:
            return self.taxon
        
        else:
            # load the taxon instance from the source

            if self.taxon_uuid and self.taxon_source:
                TaxonTreeModel = self.get_source_model()
                instance = TaxonTreeModel.objects.get(uuid=str(self.uuid)) 
                lazy_taxon = LazyTaxon(instance)
                self.set_taxon(lazy_taxon)
                
        return self.taxon


    def set_taxon(self, lazy_taxon):

        # allow setting with LazyTaxon or LazyAppTaxon
        
        self.taxon_uuid = str(lazy_taxon.taxon_uuid)
        self.taxon_nuid = lazy_taxon.taxon_nuid
        self.taxon_latname = lazy_taxon.taxon_latname
        self.taxon_source = lazy_taxon.taxon_source
        self.taxon_include_descendants = lazy_taxon.taxon_include_descendants

        # the lazy taxon, make sure it is the right LazyTaxonClass
        lazy_taxon_kwargs = {
            'taxon_uuid' : str(lazy_taxon.taxon_uuid),
            'taxon_nuid' : lazy_taxon.taxon_nuid,
            'taxon_latname' : lazy_taxon.taxon_latname,
            'taxon_source' : lazy_taxon.taxon_source,
            'taxon_include_descendants' : lazy_taxon.taxon_include_descendants,
        }
        
        self.taxon = self.LazyTaxonClass(**lazy_taxon_kwargs)


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
                return '%s (%s)' %(vernacular, self.taxon_latname)

            return self.taxon_latname
            
        return 'no taxon assigned'


    def save(self, *args, **kwargs):
        if self.taxon is not None:
            self.set_taxon(self.taxon)


        # make sure there is no taxon saved without all parameters set correctly
        taxon_required_fields = set(['taxon_source', 'taxon_nuid', 'taxon_latname', 'taxon_uuid'])

        for field_name in taxon_required_fields:

            if getattr(self, field_name, None) is not None:

                for required_field_name in taxon_required_fields:

                    required_field_value = getattr(self, required_field_name, None)

                    if required_field_value is None or len(required_field_value) == 0:
                        raise ValueError('If you add a taxon to a model, the field "{0}" is required'.format(
                            required_field_name))

                break

        super().save(*args, **kwargs)
        
        
    class Meta:
        abstract = True
    
    

'''
    ModelWithTaxon
    - taxon is optional
    - if a taxon is set, all parameters are required
'''
class ModelWithTaxon(ModelWithTaxonCommon):

    taxon_uuid = models.UUIDField(null=True)
    taxon_nuid = models.CharField(max_length=255, null=True)
    taxon_latname = models.CharField(max_length=255, null=True)
    taxon_source = models.CharField(max_length=255, null=True)

    taxon_include_descendants = models.BooleanField(default=False)

    def remove_taxon(self):
        self.taxon = None
        self.taxon_uuid = None
        self.taxon_nuid = None
        self.taxon_latname = None
        self.taxon_source = None

        self.save()


    class Meta:
        abstract = True
        
        
class ModelWithRequiredTaxon(ModelWithTaxonCommon):
    
    taxon_uuid = models.UUIDField()
    taxon_nuid = models.CharField(max_length=255)
    taxon_latname = models.CharField(max_length=255)
    taxon_source = models.CharField(max_length=255)

    taxon_include_descendants = models.BooleanField(default=False)

    class Meta:
        abstract = True
