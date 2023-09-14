from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection

from django.contrib.gis.db.models.functions import Centroid

User = get_user_model()

from django.contrib.gis.geos import GEOSGeometry

from localcosmos_server.models import UserClients, App, TaxonomicRestriction

from localcosmos_server.taxonomy.generic import ModelWithTaxon

from localcosmos_server.utils import datetime_from_cron

from djangorestframework_camel_case.util import underscoreize

from PIL import Image, ImageOps

import uuid, json, os

from .json_schemas import OBSERVATION_FORM_SCHEMA


# a list of usable dataset validation classes
DATASET_VALIDATION_CLASSPATHS = getattr(settings, 'DATASET_VALIDATION_CLASSES', ())


def import_module(module):
    module = str(module)
    d = module.rfind(".")
    module_name = module[d+1:len(module)]
    m = __import__(module[0:d], globals(), locals(), [module_name])
    return getattr(m, module_name)


DATASET_VALIDATION_CHOICES = []
DATASET_VALIDATION_CLASSES = []
DATASET_VALIDATION_DICT = {}

for classpath in DATASET_VALIDATION_CLASSPATHS:

    ValidationClass = import_module(classpath)

    verbose_name = ValidationClass.verbose_name

    choice = (classpath, verbose_name)

    DATASET_VALIDATION_CHOICES.append(choice)
    DATASET_VALIDATION_CLASSES.append(ValidationClass)
    DATASET_VALIDATION_DICT[classpath] = ValidationClass


# do not change this
# Datasets with this validation step have gone through all validation steps
# 'completed' does not mean that the dataset is valid, just that the validation process is complete
COMPLETED_VALIDATION_STEP = 'completed'


'''
    ObservationForm
'''

class ObservationForm(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    version = models.IntegerField()
    definition = models.JSONField()

    @classmethod
    def get_json_schema(cls):
        return OBSERVATION_FORM_SCHEMA

    class Meta:
        unique_together=('uuid', 'version')


'''
    MetaData
'''

class MetaData(models.Model):

    observation_form = models.ForeignKey(ObservationForm, on_delete=models.PROTECT)
    data = models.JSONField()


'''
    Dataset
    - datasets have to be validated AFTER being saved, which means going through the validation routine
    - after validation, the is_valid Bool is being set to True if validation was successful
    - LazyTaxonClass LazyAppTaxon which is default for ModelWithTaxon
'''
class Dataset(ModelWithTaxon):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    observation_form = models.ForeignKey(ObservationForm, on_delete=models.PROTECT)

    ### data
    # all data except the taxononmic inherited from ModelWithTaxon is stored in the json data column without schema
    # for quicker queries, some fields have their own (redundant) db columns below
    data = models.JSONField()
    

    meta_data = models.ForeignKey(MetaData, null=True, on_delete=models.PROTECT)

    ### redundant fields for quick DB queries
    # geographic reference, useful for anycluster and quick GIS queries
    coordinates = models.PointField(srid=3857, null=True) # point
    geographic_reference = models.GeometryField(srid=3857, null=True, blank=True) # for other geometries

    # app reference, for filtering datasets on maps, no FK to not lose data if the app is deleted
    app_uuid = models.UUIDField()

    # temporal reference, if it is a timestamp
    timestamp = models.DateTimeField(null=True)

    # if the observing entity has got an account it is linked here
    user = models.ForeignKey(User, on_delete=models.SET_NULL, to_field='uuid', null=True, blank=True)
    
    # client_id for quick lookup, if anonymous users want to fetch their datasets
    # client_id is redundant, also occurs in data
    # client_id can never be changed
    client_id = models.CharField(max_length=255, editable=False)
    platform = models.CharField(max_length=255, editable=False)


    ### fields for validation
    # the last step is always 'completed', null means validation has not yet started
    validation_step = models.CharField(max_length=255, null=True)

    # a list of errors
    validation_errors = models.JSONField(null=True)
    is_valid = models.BooleanField(default=False)


    # fields for publication
    is_published = models.BooleanField(default=True)
    

    ### flags that should not reside inside the data json because they can differ between client and server
    # following timestamps can differ between server and offline device
    # do not use auto_now_add or auto_now as these values are always set in the clients
    created_at = models.DateTimeField(editable=False) # timestamp when the dataset has been created on any of the clients
    last_modified = models.DateTimeField(null=True) # timestamp when the dataset has been alteres on any of the clients


    ###############################################################################################################
    # VALIDATION
    # - iterate over all remaining steps as defined in DatasetValidationRoutine
    # - if no steps are defined, mark the dataset as valid, and set validation_step to 'completed'
    ###############################################################################################################

        
    @property
    def validation_routine(self):

        # the app might have been deleted
        app = App.objects.filter(uuid=self.app_uuid).first()

        if app:
            return DatasetValidationRoutine.objects.filter(app=app).order_by('position')
        return []

    # validation begins at the index of self.validation_step in the routine
    def validate(self):
        validation_routine = self.validation_routine

        if self.validation_step != COMPLETED_VALIDATION_STEP:

            if len(validation_routine) > 0:

                if self.validation_step:
                    current_step = self.current_validation_step
                    
                else:
                    current_step = validation_routine[0]
                    self.validation_step = current_step.validation_class
                    self.save()
                
                
                ValidationClass = current_step.get_class()
                validator = ValidationClass(current_step)

                # on is_valid and is_invald, the validator set dataset.validation_step to the next step
                # and recursively calls dataset.validate()
                validator.validate(self)
                
            else:
                self.is_valid = True
                self.is_published = True
                self.validation_step = COMPLETED_VALIDATION_STEP

                self.save()

    @property
    def current_validation_status(self):

        if self.validation_step == COMPLETED_VALIDATION_STEP:
            return self.validation_step
        
        ValidationClass = DATASET_VALIDATION_DICT[self.validation_step]
        return ValidationClass.status_message        

    @property
    def current_validation_step(self):

        if not self.validation_step or self.validation_step == COMPLETED_VALIDATION_STEP:
            return None
        
        validation_routine = self.validation_routine
        validation_steps = list(validation_routine.values_list('validation_class', flat=True))
        current_index = validation_steps.index(self.validation_step)
        current_step = validation_routine[current_index]
        return current_step
    

    '''
    read the data column and update the redundant columns accordingly
    - this might become version specific if DatasetJSON spec or ObservationFormJSON spec change
    '''
    def update_redundant_columns(self):

        reported_values = self.data

        # never alter the user that is assigned
        # in rare cases the following can happen:
        # - loggedin user creates sighting from device.platform=browser
        # - fetching the browser device uid failed
        # -> an unassigned device_uuid is used, the logged in user is linked to the sighting
        # fix this problem and alter self.data['client_id'] to match the users browser client


        # assign a user to the observation - even if it the dataset is updated
        if not self.user and self.client_id:
            # try find a user in usermobiles
            client = UserClients.objects.filter(client_id=self.client_id).first()
            if client:
                self.user = client.user

        # AFTER assigning the user, use the browser client_id if platform is browser
        if not self.pk:

            if self.platform == 'browser' and self.user:
                    
                client = UserClients.objects.filter(user=self.user, platform='browser').order_by('pk').first()

                if client:
                    user_browser_client_id = client.client_id
                
                    if user_browser_client_id != self.client_id:
                        self.client_id = user_browser_client_id

        
        # update taxon
        # use the provided observation form json
        taxon_field_uuid = self.observation_form.definition['taxonomicReference']

        if taxon_field_uuid in reported_values and type(reported_values[taxon_field_uuid]) == dict:
            taxon_json_camel = reported_values[taxon_field_uuid]
            taxon_json = underscoreize(taxon_json_camel, no_underscore_before_number=True)

            lazy_taxon = self.LazyTaxonClass(**taxon_json)
            self.set_taxon(lazy_taxon) 
        
        # update coordinates or geographic_reference
        # {"type": "Feature", "geometry": {"crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        # "type": "Point", "coordinates": [8.703575134277346, 55.84336786584161]}, "properties": {"accuracy": 1}}
        # if it is a point, use coordinates. Otherwise use geographic_reference
        geographic_reference_field_uuid = self.observation_form.definition['geographicReference']
        if geographic_reference_field_uuid in self.data:

            reported_value = self.data[geographic_reference_field_uuid]

            srid_str = reported_value['geometry']['crs']['properties']['name']
            srid = int(srid_str.split(':')[-1])

            geojson = json.dumps(reported_value['geometry'])
            geos_geometry = GEOSGeometry(geojson, srid=srid)

            if reported_value['geometry']['type'] == 'Point':

                #longitude = reported_value['geometry']['coordinates'][0]
                #latitude = reported_value['geometry']['coordinates'][1]
                #coords = GEOSGeometry('POINT({0} {1})'.format(longitude, latitude), srid=srid)
                
                self.coordinates = geos_geometry
                self.geographic_reference = geos_geometry

            elif reported_value['geometry']['type'] == 'Polygon':
                
                self.geographic_reference = geos_geometry
                self.coordinates = self.geographic_reference.centroid

        # update temporal reference
        temporal_reference_field_uuid = self.observation_form.definition['temporalReference']
        
        if temporal_reference_field_uuid in self.data:

            reported_value = self.data[temporal_reference_field_uuid]

            if reported_value['cron']['type'] == 'timestamp' and reported_value['cron']['format'] == 'unixtime':
                self.timestamp = datetime_from_cron(reported_value)


    def nearby(self):

        queryset = []
        if self.coordinates:
            
            # City.objects.raw('SELECT id, name, %s as point from myapp_city' % (connection.ops.select % 'point'))

            fields = Dataset._meta.concrete_fields
            field_names = []

            # Relational Fields are not supported
            for field in fields:
                if isinstance(field, models.ForeignKey):
                    #name = field.get_attname_column()[0]
                    continue
                if isinstance(field, models.fields.BaseSpatialField):
                    name = connection.ops.select % field.name
                else:
                    name = field.name

                field_names.append(name)

            fields_str = ','.join(field_names)
            fields_str.rstrip(',')
        
            queryset = Dataset.objects.raw(
                '''SELECT {fields}, user_id FROM datasets_dataset WHERE id != %s
                    ORDER BY coordinates <-> st_setsrid(st_makepoint(%s,%s),3857);'''.format(
                        fields=fields_str), [self.id, self.coordinates.x, self.coordinates.y])
            
        return queryset

    @property
    def thumbnail(self):
        image = DatasetImages.objects.filter(dataset=self).first()

        if image:
            url = image.get_image_url(250, square=True)
            return url
        
        return None

    # this is not the validation routine, but the check for general localcosmos requirements
    def validate_requirements(self):
        if not self.data:
            raise ValueError('Dataset needs at least some data')

    def save(self, *args, **kwargs):

        created = False
        if not self.pk:
            if not self.created_at:
                self.created_at = timezone.now()
            created = True

        # validate the JSON
        self.validate_requirements()
        
        # update columns
        self.update_redundant_columns()

        if settings.LOCALCOSMOS_SERVER_PUBLISH_INVALID_DATA == False:
            self.is_published = False

        # this will run the validator
        super().save(*args, **kwargs)

        if created == True:
            self.validate()
     

    def __str__(self):
        if self.taxon_latname:
            return '{}'.format(self.taxon_latname)
        return str(_('Unidentified'))
    

    class Meta:
        ordering = ['-pk']



'''
    All Datasets go through the same routine
    - one validation routine per app, manageable in the app admin
    - steps can optionally depend on a taxon
'''
class DatasetValidationRoutine(ModelWithTaxon):

    app = models.OneToOneField(App, on_delete=models.CASCADE)
    
    validation_class = models.CharField(max_length=255, choices=DATASET_VALIDATION_CHOICES)
    position = models.IntegerField(default=0)

    taxonomic_restrictions = GenericRelation(TaxonomicRestriction)


    def get_class(self):
        return DATASET_VALIDATION_DICT[self.validation_class]

    def verbose_name(self):
        return DATASET_VALIDATION_DICT[self.validation_class].verbose_name

    def description(self):
        return DATASET_VALIDATION_DICT[self.validation_class].description


    def __str__(self):
        return '{0}'.format(DATASET_VALIDATION_DICT[self.validation_class].verbose_name)

    class Meta:
        unique_together = ('app', 'validation_class')
        ordering = ['position']




# Dataset Images have to be compatible with GenericForms
# - reference the field uuid
# - supply 1x 2x 4x image sizes
# - the numbers represent the width of the large side
IMAGE_SIZES = {
    'regular' : {
        '1x' : 250,
        '2x' : 500,
        '4x' : 1000,
    },
    'large' : {
        '4x' : 1000,
        '8x' : 2000,
    },
    'all' : {
        '1x' : 250,
        '2x' : 500,
        '4x' : 1000,
        '8x' : 2000,
    }
}

def dataset_image_path(instance, filename):
    return 'datasets/{0}/images/{1}/{2}'.format(str(instance.dataset.uuid), instance.field_uuid, filename)


class DatasetImages(models.Model):

    resized_folder_name = 'resized'

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='images')
    field_uuid = models.UUIDField()
    image = models.ImageField(max_length=255, upload_to=dataset_image_path)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def user(self):
        return self.dataset.user

    @property
    def client_id(self):
        return self.dataset.client_id

    @property
    def app_uuid(self):
        return self.dataset.app_uuid

    @property
    def resized_folder(self):

        folder_path = os.path.dirname(self.image.path)
        
        resized_folder = os.path.join(folder_path, self.resized_folder_name)
        if not os.path.isdir(resized_folder):
            os.makedirs(resized_folder)

        return resized_folder


    def get_resized_filename(self, size, square=False):

        filename = os.path.basename(self.image.path)
        blankname, ext = os.path.splitext(filename)

        if square:
            filename = '{0}-{1}-square{2}'.format(blankname, size, ext)
        else:
            filename = '{0}-{1}{2}'.format(blankname, size, ext)
        return filename


    def get_image_url(self, size, square=False):

        filename = self.get_resized_filename(size, square=square)

        resized_path = os.path.join(self.resized_folder, filename)

        if not os.path.isfile(resized_path):

            max_size = (size, size)

            image = Image.open(self.image.path)

            if square:
                image = ImageOps.fit(image, max_size, Image.BICUBIC)
            else:
                image.thumbnail(max_size)

            image.save(resized_path, image.format)

        image_url = os.path.join(os.path.dirname(self.image.url), self.resized_folder_name, filename)

        return image_url


    def prepend_host(self, request, url):
        host = request.get_host()
        absolute_url = '{0}://{1}{2}'.format(request.scheme, host, url)
        return absolute_url


    def image_urls(self, request=None):

        image_urls = {}
        
        for size_name, image_size in IMAGE_SIZES['all'].items():
            # create the resized image, respecting which side is the longer one
            image_url = self.get_image_url(image_size)
            if request != None:
                image_url = self.prepend_host(request, image_url)
            image_urls[size_name] = image_url

        return image_urls


    def __str__(self):
        if self.dataset.taxon_latname:
            return self.dataset.taxon_latname
        
        return 'Dataset Image #{0}'.format(self.id)
    
        
'''
    USER Geometry
    max 3 per user
'''
class UserGeometry(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    geometry = models.GeometryField(srid=3857, null=True, blank=True)
    name = models.CharField(max_length=355)
