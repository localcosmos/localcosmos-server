import urllib.request, json, codecs # gbif_id
from urllib.parse import quote_plus
from http.client import RemoteDisconnected

from django.conf import settings

SUPPORTED_LAZY_TAXONOMY_SOURCES = []
if hasattr(settings, 'LAZY_TAXONOMY_SOURCES'):
    SUPPORTED_LAZY_TAXONOMY_SOURCES = [db[0] for db in settings.LAZY_TAXONOMY_SOURCES]

##################################################################################################################
#
# LazyTaxon
# - the LazyTaxon class is the only taxon class that should be used directly by LocalCosmos
# - it is compatible with all taxonomic sources
# - LazyTaxon.source has to point to the source it comes from, eg taxonomy.sources.col
#
# LazyTaxon can be instantiated in two ways:
#   1. passing an instance, eg a subclass of ModelWithRequiredTaxon, or a sibclass of TaxonTree
#   2. passing the 4 required parameters uuid, nuid, latname, source
#

class LazyTaxonBase:

    def __init__(self, *args, **kwargs):

        self.instance = None # either ModelwithTaxon Subclass or a TaxonTree Subclass

        if 'instance' in kwargs:

            self.instance = kwargs['instance']

            self.taxon_latname = self.instance.taxon_latname
            self.taxon_author = self.instance.taxon_author
            self.taxon_include_descendants = getattr(self.instance, 'taxon_include_descendants', False)

            # these values change across tree versions
            self.name_uuid = str(self.instance.name_uuid)
            self.taxon_nuid = self.instance.taxon_nuid

            self.origin = self.instance.__class__.__name__

            taxon_source = self.get_taxon_source(self.instance)

            if not taxon_source:
                raise ValueError('Non-taxonomic instance passed to LazyTaxon. Could not determine taxon_source.')

            self.taxon_source = taxon_source


        elif 'taxon_latname' in kwargs and 'taxon_author' in kwargs and 'taxon_source' in kwargs and 'taxon_nuid' in kwargs and 'name_uuid' in kwargs:
            self.taxon_latname = kwargs['taxon_latname']
            self.taxon_author = kwargs['taxon_author']
            self.taxon_source = kwargs['taxon_source']
            self.taxon_include_descendants = kwargs.get('taxon_include_descendants', False)

            self.taxon_nuid = kwargs['taxon_nuid']
            self.name_uuid = kwargs['name_uuid']

        else:
            raise ValueError('Unable to instantiate LazyTaxon, improper parameters given: %s' %kwargs)


    def get_taxon_source(self, instance):

        taxon_source = None
        
        # if the instance has an attribute taxon_source it derives from ModelWithTaxonCommon
        # if the instance has an attribute source_id it derives from the DB - might be deprecated

        if hasattr(instance, 'taxon_source'):
            taxon_source = instance.taxon_source                

        # in this case, it is a taxon directly from the taxonomic database
        else:
            # remove ".models" from module
            taxon_source = ('.').join(instance.__module__.split('.')[:-1])
            #self.taxon_source = 'taxonomy.sources.%s' % instance._meta.app_label

            if taxon_source not in SUPPORTED_LAZY_TAXONOMY_SOURCES:
                supported_taxonomic_sources = ','.join(SUPPORTED_LAZY_TAXONOMY_SOURCES)
                raise ValueError('unsupported taxonomic source passed to LazyTaxon. {0} not in {1}'.format(taxon_source, supported_taxonomic_sources))
        
        return taxon_source
    

    def gbif_nubKey(self):

        gbif_nubKey = None

        url = 'http://api.gbif.org/v1/species?name=%s' % quote_plus(self.taxon_latname.encode('utf-8'))

        request = urllib.request.Request(url)

        try:
            response = urllib.request.urlopen(request)
        except (urllib.error.URLError, RemoteDisconnected) as e:
            return None
            
        if response.getcode() == 200:

            codec = response.headers.get_content_charset()

            if codec == None:
                codec = 'utf-8'

            reader = codecs.getreader(codec)
            data = json.load(reader(response))
            
            if 'results' in data:
                results = data['results']
                if len(results) >0 and 'nubKey' in results[0]:
                    gbif_nubKey = results[0]['nubKey']

        return gbif_nubKey


    #############################################################################################################
    # bootstrap specific outputs
    def as_typeahead_choice(self, label=None):

        if label is None:
            label = self.taxon_latname
        
        obj = {
            'label': label,
            'taxon_latname': self.taxon_latname,
            'taxon_author': self.taxon_author,
            'taxon_nuid': self.taxon_nuid,
            'taxon_source' : self.taxon_source,
            'name_uuid': str(self.name_uuid),
        }
        return obj

    def as_json(self):
        obj = {
            'taxonLatname': self.taxon_latname,
            'taxonAuthor': self.taxon_author,
            'taxonNuid': self.taxon_nuid, 
            'taxonSource' : self.taxon_source,
            'nameUuid': self.name_uuid,
        }

        return obj

    # returns if the taxon is within the restriction
    def check_restrictions(self, taxonomic_restrictions):
        # restriction type can be 'exists' or 'optional' or 'required'
        if taxonomic_restrictions.exists():

            for taxonomic_restriction in taxonomic_restrictions:

                if taxonomic_restriction.taxon_latname == self.taxon_latname and taxonomic_restriction.taxon_author == self.taxon_author:
                    return True

            return False
        
        return True


    # default str output
    def __str__(self):
        if self.taxon_author:
            return '{0} {1}'.format(self.taxon_latname, self.taxon_author)
        
        return self.taxon_latname

    def __eq__(self, other):

        if other and isinstance(other, LazyTaxonBase):
            if self.taxon_source == other.taxon_source and self.taxon_latname == other.taxon_latname and self.taxon_author == self.taxon_author and str(self.name_uuid) == str(other.name_uuid):
                return True
        return False
    

##################################################################################################################
#
# AppTaxon
# - taxon read from app
# - apps provide taxa by source (folder) and uuid (filename)
# - Datasets can be passed as an instance
#

class LazyAppTaxon(LazyTaxonBase):
    pass


##################################################################################################################
#
# LazyTaxonList
# - a QuerySet - like TaxonList containig LazyTaxa
# - manage taxon queries
# - initially it just stores querysets and does not hit the db
        
from django.core.exceptions import FieldError

class LazyTaxonListBase:
    
    def __init__(self, queryset=None):

        if not hasattr(self, 'LazyTaxonClass'):
            raise ValueError('LazyTaxonList needs the attribute LazyTaxonClass')
        
        self.querysets = []
        self.name_uuids = []
        self.taxonlist = None
        
        if queryset is not None:
            self.add(queryset)

    def add(self, queryset):
        self.querysets.append(queryset)


    def add_lazy_taxon_list(self, lazy_taxon_list):
        for queryset in lazy_taxon_list.querysets:
            self.querysets.append(queryset)

    def sorted_taxa(self):

        self.taxonlist = []

        for queryset in self.querysets:
            for instance in queryset:
                taxon = self.LazyTaxonClass(instance)
                self.name_uuids.append(str(taxon.name_uuid))
                self.taxonlist.append(taxon)
        
        return self.taxonlist

    def taxa(self):
        self.taxonlist = []

        for queryset in self.querysets:
            
            # this is just a safety precaution filtering out all entries without taxa
            queryset = queryset.exclude(name_uuid=None)
            
            for instance in queryset:
                taxon = self.LazyTaxonClass(instance=instance)
                self.name_uuids.append(taxon.name_uuid)
                self.taxonlist.append(taxon)

        return self.taxonlist


    def uuids(self):
        if self.taxonlist is None:
            taxonlist = self.taxa()

        return self.name_uuids


    def filter(self, **kwargs):
        # linked taxa can be filtered by include_descendants, TaxonTree can not
        for index, queryset in enumerate(self.querysets):

            if 'taxon_include_descendants' in kwargs and hasattr(queryset.model, 'taxon_include_descendants') == False:
                taxon_include_descendants = kwargs.pop('taxon_include_descendants')
                if taxon_include_descendants == True:
                    self.querysets[index] = queryset.none()
                else:
                    # if include_descendants = False, this query applies to tree taxa, which are taxon_include_descendants = False by design
                    self.querysets[index] = queryset.filter(**kwargs)
            else:
                self.querysets[index] = queryset.filter(**kwargs)

    def exclude(self, **kwargs):
        for index, queryset in enumerate(self.querysets):
            self.querysets[index] = queryset.exclude(**kwargs)

    # check if a taxon is included in the taxonlist - respecting descendants
    # each queryset is evaluated separetely. if a match has been found, no more querysets are evaluated
    def included_in_descendants(self, lazy_taxon):

        for queryset in self.querysets:

            for taxon in queryset:
                if lazy_taxon.taxon_nuid.startswith(taxon.taxon_nuid):
                    return True

        return False

    # search for a taxon in all taxa
    # each queryset is evaluated separetely. if a match has been found, no more querysets are evaluated
    def included_in_taxa(self, lazy_taxon):

        for queryset in self.querysets:

            for taxon in queryset:
                if lazy_taxon.taxon_latname == taxon.taxon_latname and lazy_taxon.taxon_author == taxon.taxon_author:
                    return True

        return False


    def count(self):
        count = 0

        for queryset in self.querysets:
            count += queryset.count()

        return count


    def fetch(self, limit=10, **kwargs):
        
        return_type = kwargs.get('return_type', 'instance')
        results = []

        for queryset in self.querysets:
            if len(results) >= limit:
                break

            for taxon in queryset[:limit]:

                if len(results) >= limit:
                    break
                
                lazy_taxon = self.LazyTaxonClass(instance=taxon)
                    
                if return_type == 'typeahead':
                    results.append(lazy_taxon.as_typeahead_choice())
                else:
                    results.append(lazy_taxon)
                    
        return results


    def __iter__(self):
        for queryset in self.querysets:
            for taxon in queryset:
                yield self.LazyTaxonClass(instance=taxon)

    def __getitem__(self, i):
        return self.taxa()[i]

    ''' this is a copy of django QuerySet.__getitem__ which is necessary for pagination
    one day this should be implemented in a working way to make pagination better than fetching all taxa into a list
    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0)) or
                (isinstance(k, slice) and (k.start is None or k.start >= 0) and
                 (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        if self._result_cache is not None:
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.query.set_limits(start, stop)
            return list(qs)[::k.step] if k.step else qs

        qs = self._clone()
        qs.query.set_limits(k, k + 1)
        return list(qs)[0]
    '''


class LazyTaxonList(LazyTaxonListBase):
    
    LazyTaxonClass = LazyAppTaxon
