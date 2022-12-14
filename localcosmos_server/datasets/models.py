from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection

User = get_user_model()

from django.contrib.gis.geos import GEOSGeometry

from localcosmos_server.models import UserClients, App, TaxonomicRestriction

from localcosmos_server.taxonomy.generic import ModelWithTaxon

from localcosmos_server.utils import datetime_from_cron

from datetime import datetime, timezone, timedelta

from PIL import Image, ImageOps

import uuid, json, os


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
'''
class ObservationForm(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    version = models.TextField()
    definition = models.JSONField()

    class Meta:
        unique_together=('uuid', 'version')

'''
'''
    MetaData
'''
'''
class MetaData(models.Model):

    observation_form = models.ForeignKey(ObservationForm, on_delete=models.PROTECT)
    data = models.JSONField()
'''

'''
    Dataset
    - datasets have to be validated AFTER being saved, which means going through the validation routine
    - after validation, the is_valid Bool is being set to True if validation was successful
    - LazyTaxonClass LazyAppTaxon which is default for ModelWithTaxon
'''
class Dataset(ModelWithTaxon):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    ### data
    # all data except the taxononmic inherited from ModelWithTaxon is stored in the json data column without schema
    # for quicker queries, some fields have their own (redundant) db columns below
    data = models.JSONField()
    #observation_form = models.ForeignKey(ObservationForm, on_delete=models.PROTECT)

    #meta_data = models.ForeignKey(MetaData, null=True, on_delete=models.PROTECT)

    ### redundant fields for quick DB queries
    # geographic reference, useful for anycluster and quick GIS queries
    coordinates = models.PointField(srid=3857, null=True) # point
    geographic_reference = models.GeometryField(srid=3857, null=True, blank=True) # for other geometries

    # app reference, for filtering datasets on maps, no FK to not lose data if the app is deleted
    # app_uuid is transmitted by django_road, settings editable=False breaks django-rest-framework
    app_uuid = models.UUIDField()

    # temporal reference, if it is a timestamp
    timestamp = models.DateTimeField(null=True)

    # if the observing entity has got an account it is linked here
    user = models.ForeignKey(User, on_delete=models.SET_NULL, to_field='uuid', null=True, blank=True)
    
    # client_id for quick lookup, if anonymous users want to fetch their datasets
    # client_id is redundant, also occurs in data
    # client_id can never be changed
    client_id = models.CharField(max_length=255, editable=False)


    ### fields for validation
    # the last step is always 'completed', null means validation has not yet started
    validation_step = models.CharField(max_length=255, null=True)

    # a list of errors
    validation_errors = models.JSONField(null=True)
    is_valid = models.BooleanField(default=False)
    

    ### flags that should not reside inside the data json because they can differ between client and server
    # following timestamps can differ between server and offline device
    # do not use auto_now_add or auto_now as these values are always set by django_road in the clients
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

        reported_values = self.data['dataset']['reported_values']

        # never alter the user that is assigned
        # in rare cases the following can happen:
        # - loggedin user creates sighting from device.platform=browser
        # - fetching the browser device uid failed
        # -> an unassigned device_uuid is used, the logged in user is linked to the sighting
        # fix this problem and alter self.data['client_id'] to match the users browser client
        if not self.pk:

            # fill self.client_id
            client_id = reported_values['client_id']
            self.client_id = client_id

        # assign a user to the observation - even if it the dataset is updated
        if not self.user and self.client_id:
            # try find a user in usermobiles
            client_id = reported_values['client_id']
            self.client_id = client_id
            client = UserClients.objects.filter(client_id=client_id).first()
            if client:
                self.user = client.user

        # AFTER assigning the user, use the browser client_id if platform is browser
        if not self.pk:

            platform = reported_values['client_platform']

            # use browser client_id if browser and self.user
            # this is only possible if the dataset has been transmitted using django_road, which assigned a user
            if platform == 'browser' and self.user:
                    
                client = UserClients.objects.filter(user=self.user, platform='browser').order_by('pk').first()

                if client:

                    user_browser_client_id = client.client_id
                
                    if user_browser_client_id != reported_values['client_id']:
                        self.data['dataset']['reported_values']['client_id'] = user_browser_client_id
                        self.client_id = user_browser_client_id

        
        # update taxon
        # use the provided observation form json

        observation_form = self.data['dataset']['observation_form']
        
        taxon_field_uuid = observation_form['taxonomic_reference']

        if taxon_field_uuid in reported_values and type(reported_values[taxon_field_uuid]) == dict:
            taxon_json = reported_values[taxon_field_uuid]

            lazy_taxon = self.LazyTaxonClass(**taxon_json)
            self.set_taxon(lazy_taxon) 
        
        # update coordinates or geographic_reference
        # {"type": "Feature", "geometry": {"crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        # "type": "Point", "coordinates": [8.703575134277346, 55.84336786584161]}, "properties": {"accuracy": 1}}
        # if it is a point, use coordinates. Otherwise use geographic_reference
        geographic_reference_field_uuid = self.data['dataset']['observation_form']['geographic_reference']
        if geographic_reference_field_uuid in self.data['dataset']['reported_values']:

            reported_value = self.data['dataset']['reported_values'][geographic_reference_field_uuid]
            if reported_value['geometry']['type'] == 'Point':

                longitude = reported_value['geometry']['coordinates'][0]
                latitude = reported_value['geometry']['coordinates'][1]
                coords = GEOSGeometry('POINT({0} {1})'.format(longitude, latitude), srid=4326)
                
                self.coordinates = coords
                self.geographic_reference = coords


        # update temporal reference
        temporal_reference_field_uuid = self.data['dataset']['observation_form']['temporal_reference']
        
        if temporal_reference_field_uuid in self.data['dataset']['reported_values']:

            reported_value = self.data['dataset']['reported_values'][temporal_reference_field_uuid]

            # {"cron": {"type": "timestamp", "format": "unixtime", "timestamp": 1564566855177}, "type": "Temporal"}}
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


    def thumbnail_url(self):
        image = DatasetImages.objects.filter(dataset=self).first()

        if image:
            return image.thumbnail()
        
        return None

    # this is not the validation routine, but the check for general localcosmos requirements
    def validate_requirements(self):
        if self.data is None:
            raise ValueError('Dataset needs at least some data')

        reported_values = self.data['dataset']['reported_values']

        if 'client_id' not in reported_values or reported_values['client_id'] == None or len(reported_values['client_id']) == 0:
            raise ValueError('no client_id found in dataset.reported_values')


    def save(self, *args, **kwargs):

        created = False
        if not self.pk:
            created = True

        # validate the JSON
        self.validate_requirements()
        
        # update columns
        self.update_redundant_columns()

        # this will run the validator
        super().save(*args, **kwargs)

        if created == True:
            self.validate()
     
    '''
    def __str__(self):
        if self.taxon_latname:
            return '{}'.format(self.taxon_latname)
        return str(_('Unidentified'))
    '''
    

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



def dataset_image_path(instance, filename):
    return 'datasets/{0}/images/{1}/{2}'.format(str(instance.dataset.uuid), instance.field_uuid, filename)

# Dataset Images have to be compatible with GenericForms
# - reference the field uuid
# - supply a thumbnail
class DatasetImages(models.Model):

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    field_uuid = models.UUIDField()
    image = models.ImageField(max_length=255, upload_to=dataset_image_path)

    @property
    def user(self):
        return self.dataset.user

    def get_thumb_filename(self, size=100):

        filename = os.path.basename(self.image.path)
        blankname, ext = os.path.splitext(filename)

        thumbname = '{0}-{1}{2}'.format(blankname, size, ext)
        return thumbname


    def get_thumbfolder(self):

        folder_path = os.path.dirname(self.image.path)
        
        thumbfolder = os.path.join(folder_path, 'thumbnails')
        if not os.path.isdir(thumbfolder):
            os.makedirs(thumbfolder)

        return thumbfolder
    

    def get_image_format(self, image):

        if image.format:
            image_format = image.format
        else:
            image_format = 'JPEG'

        return image_format
    

    # thumbnails are always square
    def thumbnail(self, size=100):

        thumb_size = (size, size)

        image_path = self.image.path
        
        thumbfolder = self.get_thumbfolder()

        thumbname = self.get_thumb_filename(size)
        thumbpath = os.path.join(thumbfolder, thumbname)

        if not os.path.isfile(thumbpath):

            imageFile = Image.open(image_path)

            thumb_format = self.get_image_format(imageFile)

            thumb = ImageOps.fit(imageFile, thumb_size, Image.BICUBIC)

            thumb.save(thumbpath, thumb_format)
        
        thumburl = os.path.join(os.path.dirname(self.image.url), 'thumbnails', thumbname)
        return thumburl


    def resized(self, name, max_size=[1920, 1080]):

        thumbfolder = self.get_thumbfolder()

        filename = os.path.basename(self.image.path)
        blankname, ext = os.path.splitext(filename)
        thumbname = '{0}-{1}{2}'.format(filename, name, ext)

        thumbpath = os.path.join(thumbfolder, thumbname)

        if max_size[0] <= max_size[1]:
            short_edge = max_size[0]
            long_edge = max_size[1]
        else:
            short_edge = max_size[1]
            long_edge = max_size[0]

        if not os.path.isfile(thumbpath):

            image_path = self.image.path
            imageFile = Image.open(image_path)

            if imageFile.width >= imageFile.height:
                size = (long_edge, short_edge)
            else:
                size = (short_edge, long_edge)

            if imageFile.width > size[0] or imageFile.height > size[1]:
                imageFile.thumbnail(size, Image.BICUBIC)

            image_format = self.get_image_format(imageFile)
                
            imageFile.save(thumbpath, image_format)

        thumburl = os.path.join(os.path.dirname(self.image.url), 'thumbnails', thumbname)
        return thumburl

        
    # full hd image, 1920x1080 or 1080x1920
    def full_hd(self):
        return self.resized('fullhd', max_size=[1920,1080])


    def __str__(self):
        if self.dataset.taxon_latname:
            return self.dataset.taxon_latname
        
        return 'Dataset Image #{0}'.format(self.id)
    
        
