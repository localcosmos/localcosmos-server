###################################################################################################################
#
# TESTS FOR MODELS
# - this file only covers settings.LOCALCOSMOS_OPEN_SOURCE == True
#
###################################################################################################################
from django.conf import settings
from django.test import TestCase
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files import File
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from django.utils import timezone

from localcosmos_server.datasets.models import (Dataset, DatasetValidationRoutine, DatasetImages,
                                                DATASET_VALIDATION_CHOICES, DATASET_VALIDATION_DICT)

from localcosmos_server.models import UserClients, TaxonomicRestriction

from localcosmos_server.tests.common import (test_settings, TEST_IMAGE_PATH, TEST_CLIENT_ID, TEST_UTC_TIMESTAMP,
                                             TEST_TIMESTAMP_OFFSET, TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS,
                                             TEST_LATITUDE, TEST_LONGITUDE, LARGE_TEST_IMAGE_PATH)

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithDataset

from datetime import timedelta, timezone as py_timezone, datetime

from PIL import Image, ImageOps

import uuid, os, copy


def timestamp_from_utc_with_offset(utc, offset):
    delta_minutes = 0-offset
    tz = py_timezone(
        timedelta(minutes=delta_minutes)
    )
    local = (utc / 1000) + (delta_minutes * 60)

    timestamp = datetime.fromtimestamp(local, tz=tz)
    return timestamp

TEST_TIMESTAMP = timestamp_from_utc_with_offset(TEST_UTC_TIMESTAMP, TEST_TIMESTAMP_OFFSET)

mercator_srid = SpatialReference(4326)
database_srid = SpatialReference(3857)
trans_4326_to_3857 = CoordTransform(mercator_srid, database_srid)


TEST_DATA_2 = {
    "type": "Dataset",
    "dataset": {
        "type": "Observation",
        "properties": {},
        "reported_values": {
            "client_id": "f6a7f83a-7b2e-4fbc-8f1a-168904231aaf",
            "client_platform": "browser",
            "0f444e85-e31d-443d-afd3-2fa35df08ce3": {"cron": {"type": "timestamp", "format": "unixtime", "timestamp": 1576236681011, "timezone_offset": -60}, "type": "Temporal"},
            "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce": {"taxon_nuid": "006002009001005005002", "name_uuid": "77380de8-8087-41b4-9577-67b929593b0b", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Larix decidua", "taxon_author":"Linnaeus"},
            "96e8ff3b-ffcc-4ccd-b81c-542f37ce53d0": None,
            "a4d53718-715f-4436-9b4c-09fce7978153": {"type": "Feature", "geometry": {"crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "type": "Point", "coordinates": [11.079045867921542, 49.66298305845603]}, "properties": {"accuracy": 1}}
        },
        "observation_form": {
            "name": "Baumbeobachtung",
            "uuid": "c07271c1-3d36-430c-aa4d-bfbb8cb279fa",
            "fields": [
                {"role": "taxonomic_reference", "uuid": "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce", "options": {}, "version": 1, "position": -3, "definition": {"label": "Baumart", "widget": "BackboneTaxonAutocompleteWidget", "initial": None, "required": True, "help_text": None, "is_sticky": False},"field_class": "TaxonField", "widget_attrs": {}, "taxonomic_restriction": []},
                {"role": "geographic_reference", "uuid": "a4d53718-715f-4436-9b4c-09fce7978153", "options": {}, "version": 1, "position": -2, "definition": {"label": "Ort", "widget": "MobilePositionInput", "initial": None, "required": True, "help_text": None, "is_sticky": False}, "field_class": "PointJSONField", "widget_attrs": {}, "taxonomic_restriction": []},
                {"role": "temporal_reference", "uuid": "0f444e85-e31d-443d-afd3-2fa35df08ce3", "options": {}, "version": 1, "position": -1, "definition": {"label": "Zeitpunkt", "widget": "SelectDateTimeWidget", "initial": None, "required": True, "help_text": None, "is_sticky": False}, "field_class": "DateTimeJSONField", "widget_attrs": {}, "taxonomic_restriction": []},
                {"role": "regular", "uuid": "96e8ff3b-ffcc-4ccd-b81c-542f37ce53d0", "options": {}, "version": 1, "position": 4, "definition": {"label": "Eichenprozessionsspinner", "widget": "CheckboxInput", "initial": None, "required": False, "help_text": None, "is_sticky": False}, "field_class": "BooleanField", "widget_attrs": {}, "taxonomic_restriction": [{"taxon_nuid": "00600200700q003007", "name_uuid": "99000227-c450-4eb4-a6e4-e974d587cdd8", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Quercus", "restriction_type": "exists"}]},
                {"role": "regular", "uuid": "85e8e05c-5a60-46f8-b49c-b6debbe19997", "options": {}, "version": 1, "position": 5, "definition": {"label": "Bilder", "widget": "CameraAndAlbumWidget", "initial": None, "required": False, "help_text": None, "is_sticky": False}, "field_class": "PictureField", "widget_attrs": {}, "taxonomic_restriction": []}
                ],
            "options": {},
            "version": 2,
            "global_options": {},
            "temporal_reference": "0f444e85-e31d-443d-afd3-2fa35df08ce3",
            "taxonomic_reference": "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce",
            "geographic_reference": "a4d53718-715f-4436-9b4c-09fce7978153",
            "taxonomic_restriction": []
        },
    "specification_version": 1
    },
    "properties": {"thumbnail": {"url": None}}
}


# add all available validation routines,no taxonomic restricitons
class WithValidationRoutine:

    def create_validation_routine(self):

        for position, choice_tuple in enumerate(DATASET_VALIDATION_CHOICES):
            validation_class = choice_tuple[0]

            step = DatasetValidationRoutine(
                app=self.app,
                validation_class=validation_class,
                position = position,
            )
            step.save()


    def create_restricted_validation_routine(self, lazy_taxon):
        pass


@test_settings
class TestDataset(WithValidationRoutine, WithDataset, WithApp, WithUser, TestCase):


    # this also tests update_redundant_columns
    def test_save_without_validation_routine(self):

        dataset = self.create_dataset()

        # fetch the dataset to perform coordinate transformation
        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertTrue(dataset.is_valid)
        self.assertEqual(dataset.data, TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS)
        self.assertEqual(dataset.validation_step, 'completed')
        self.assertEqual(dataset.client_id, TEST_CLIENT_ID)

        self.assertEqual(dataset.timestamp, TEST_TIMESTAMP)

        point = Point(TEST_LONGITUDE, TEST_LATITUDE, srid=4326)
        point.transform(trans_4326_to_3857)

        self.assertEqual(dataset.coordinates.srid, 3857)

        # django stores 9 decimal digits
        self.assertEqual('%.8f' % dataset.coordinates.x, '%.8f' % point.x)
        self.assertEqual('%.8f' %dataset.coordinates.y, '%.8f' % point.y)
        self.assertEqual('%.8f' %dataset.geographic_reference.x, '%.8f' % point.x)
        self.assertEqual('%.8f' %dataset.geographic_reference.y, '%.8f' % point.y)
        
        self.assertEqual(dataset.app_uuid, self.app.uuid)

        self.assertEqual(dataset.user, None)
        self.assertEqual(dataset.validation_errors, None)


    # in this case, the first (and only) validation step is a human interaction step
    # if it were an automatic step, the test would have to be different
    def test_save_with_validation_routine(self):

        self.create_validation_routine()

        dataset = self.create_dataset()

        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertFalse(dataset.is_valid)
        self.assertEqual(dataset.validation_step, DATASET_VALIDATION_CHOICES[0][0])
        

    def test_save_with_user(self):

        user = self.create_user()

        client_link = UserClients(
            user = user,
            client_id = TEST_CLIENT_ID,
            platform = 'browser',
        )

        client_link.save()

        dataset = self.create_dataset()

        # fetch the dataset to perform coordinate transformation
        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertEqual(dataset.user, user)
        

    def test_validation_routine(self):

        dataset = self.create_dataset()

        self.assertEqual(dataset.validation_routine.count(), 0)
        
        # test with existing validation_routine
        self.create_validation_routine()

        dataset_2 = self.create_dataset()

        self.assertEqual(dataset_2.validation_routine.count(), len(DATASET_VALIDATION_CHOICES))


    # this is currently covered by test_save, as Dataset.save() triggers Dataset.validate()
    def test_validate(self):
        pass

    def test_current_validation_status(self):

        dataset = self.create_dataset()

        self.assertEqual(dataset.current_validation_status, 'completed')
        
        # test with existing validation_routine
        self.create_validation_routine()

        dataset_2 = self.create_dataset()

        step = DATASET_VALIDATION_DICT[DATASET_VALIDATION_CHOICES[0][0]]

        self.assertEqual(dataset_2.current_validation_status, step.status_message)
        

    def test_current_validation_step(self):

        dataset = self.create_dataset()

        self.assertEqual(dataset.current_validation_step, None)
        
        # test with existing validation_routine
        self.create_validation_routine()

        dataset_2 = self.create_dataset()

        first_step = DatasetValidationRoutine.objects.filter(app=self.app).order_by('position').first()
        
        self.assertEqual(dataset_2.current_validation_step, first_step)
        

    def test_use_existing_client_id(self):

        # emulate django_road and assign a user during the first dataset save(),
        # but the dataset contains an unknown client_id AND the platform is the browser

        user = self.create_user()

        existing_client_id = 'existing_client_id'

        client_link = UserClients(
            user = user,
            client_id = existing_client_id,
            platform = 'browser',
        )

        client_link.save()

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS,
            created_at = timezone.now(),
            user = user,
        )

        dataset.save()

        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertEqual(dataset.client_id, existing_client_id)
        self.assertEqual(dataset.data['dataset']['reported_values']['client_id'], existing_client_id)
    
    # test the following:
    # dataset .client_id, .user, .coordinates, .geographic_reference , .timestamp
    def test_update_redundant_columns(self):    

        # tests for update_redundant_columns if the dataset is created are covered by test_save()
        # the following tests are for the case if a dataset is being updated

        dataset = self.create_dataset()

        dataset = Dataset.objects.get(pk=dataset.pk)

        # alter all test data
        test_data = copy.deepcopy(TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS)

        altered_timestamp = 1576161198595

        altered_latitude = TEST_LATITUDE + 1
        altered_longitude = TEST_LONGITUDE + 1

        altered_taxon_nuid = "006002009001005005002"
        altered_name_uuid = "77380de8-8087-41b4-9577-67b929593b0b"
        altered_taxon_source = "taxonomy.sources.col"
        altered_taxon_latname =  "Larix decidua"
        altered_taxon_author = "Linnaeus 12345"


        alterations = {
            "reported_values": {
                "client_id": TEST_CLIENT_ID,
                "client_platform": "browser",
                "0f444e85-e31d-443d-afd3-2fa35df08ce3": {
                    "cron": {
                        "type": "timestamp",
                        "format": "unixtime",
                        "timestamp": altered_timestamp,
                        "timezone_offset": TEST_TIMESTAMP_OFFSET
                    },
                    "type": "Temporal"
                },
                "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce": {
                    "taxon_nuid": altered_taxon_nuid,
                    "name_uuid": altered_name_uuid,
                    "taxon_source": altered_taxon_source,
                    "taxon_latname": altered_taxon_latname,
                    "taxon_author" : altered_taxon_author,
                },
                "96e8ff3b-ffcc-4ccd-b81c-542f37ce53d0": None,
                "a4d53718-715f-4436-9b4c-09fce7978153": {
                    "type": "Feature",
                    "geometry": {
                        "crs": {
                            "type": "name", "properties": {"name": "EPSG:4326"}
                        },
                        "type": "Point",
                        "coordinates": [altered_longitude, altered_latitude]
                    },
                    "properties": {"accuracy": 1}
                }
            }
        }

        for key, value in alterations['reported_values'].items():

            test_data['dataset']['reported_values'][key] = value

        dataset.data = test_data
        dataset.save()

        dataset = Dataset.objects.get(pk=dataset.pk)

        point = Point(altered_longitude, altered_latitude, srid=4326)
        point.transform(trans_4326_to_3857)

        self.assertEqual(dataset.coordinates.srid, 3857)

        # django stores 9 decimal digits
        self.assertEqual('%.7f' % dataset.coordinates.x, '%.7f' % point.x)
        self.assertEqual('%.7f' % dataset.coordinates.y, '%.7f' % point.y)
        self.assertEqual('%.7f' % dataset.geographic_reference.x, '%.7f' % point.x)
        self.assertEqual('%.7f' % dataset.geographic_reference.y, '%.7f' % point.y)

        new_timestamp = timestamp_from_utc_with_offset(altered_timestamp, TEST_TIMESTAMP_OFFSET)
        self.assertEqual(new_timestamp, dataset.timestamp)

        self.assertEqual(dataset.taxon.taxon_latname, altered_taxon_latname)
        self.assertEqual(dataset.taxon.name_uuid, altered_name_uuid)
        self.assertEqual(dataset.taxon.taxon_source, altered_taxon_source)
        self.assertEqual(dataset.taxon.taxon_nuid, altered_taxon_nuid)


    def test_nearby(self):

        dataset = self.create_dataset()
        user = self.create_user()

        dataset_2 = Dataset(
            app_uuid = self.app.uuid,
            data = TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS,
            created_at = timezone.now(),
            user = user,
        )

        dataset_2.save()

        dataset = Dataset.objects.get(pk=dataset.pk)

        nearby = dataset.nearby()

        self.assertEqual(len(nearby), 1)

        nearby_dataset = nearby[0]
        self.assertEqual(nearby_dataset.pk, dataset_2.pk)
        self.assertEqual(nearby_dataset.user, user)


    def test_validate_requirements(self):

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = None,
        )

        with self.assertRaises(ValueError):
            dataset.validate_requirements()


        test_data = copy.deepcopy(TEST_DATA_2)
        del test_data['dataset']['reported_values']['client_id']

        dataset.data = test_data

        with self.assertRaises(ValueError):
            dataset.validate_requirements()

        test_data['dataset']['reported_values']['client_id'] = None
        dataset.data = test_data

        with self.assertRaises(ValueError):
            dataset.validate_requirements()


        test_data['dataset']['reported_values']['client_id'] = ''
        dataset.data = test_data

        with self.assertRaises(ValueError):
            dataset.validate_requirements()
        

    def test_str(self):
        # test with and without taxon_latname
        dataset = self.create_dataset()

        self.assertEqual(str(dataset), 'Picea abies')


        test_data = copy.deepcopy(TEST_DATA_2)
        # delete the taxon

        taxon_field_uuid = test_data['dataset']['observation_form']['taxonomic_reference']
        del test_data['dataset']['reported_values'][taxon_field_uuid]

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = test_data,
            created_at = timezone.now(),
        )

        dataset.save()

        self.assertEqual(str(dataset), str(_('Unidentified')))

@test_settings
class TestDatasetWithMedia(WithMedia, WithDataset, WithApp, WithUser, TestCase):

    def test_thumbnail_url(self):

        # first, test dataset without images
        dataset = self.create_dataset()

        dataset = Dataset.objects.get(pk=dataset.pk)

        thumbnail = dataset.thumbnail_url()
        self.assertEqual(thumbnail, None)

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset=dataset,
            field_uuid=uuid.uuid4(),
            image=image,
        )

        dataset_image.save()

        thumbnail = dataset.thumbnail_url()
        self.assertTrue(thumbnail.endswith('.jpg'))
    

from localcosmos_server.datasets.validation.base import DatasetValidatorBase
from localcosmos_server.taxonomy.lazy import LazyAppTaxon

@test_settings
class TestDatasetValidationRoutine(WithValidationRoutine, WithApp, TestCase):

    def test_get_class(self):

        self.create_validation_routine()

        steps = DatasetValidationRoutine.objects.all()

        for step in steps:
            validation_class = step.get_class()
            self.assertTrue(issubclass(validation_class, DatasetValidatorBase))

            #
            verbose_name = step.verbose_name()
            description = step.description()
            
            self.assertEqual(str(verbose_name), str(step))
            

    def test_taxonomic_restriction(self):

        test_taxon_kwargs = {
            "taxon_source": "taxonomy.sources.col",
            "name_uuid": "eb53f49f-1f80-4505-9d56-74216ac4e548",
            "taxon_nuid": "006002009001005001001",
            "taxon_latname": "Abies alba",
            "taxon_author" : "Linnaeus",
            "gbif_nubKey": 2685484,
        }
        lazy_taxon = LazyAppTaxon(**test_taxon_kwargs)

        self.create_validation_routine()

        step = DatasetValidationRoutine.objects.first()
        
        restriction = TaxonomicRestriction(
            taxon = lazy_taxon,
            content_type = ContentType.objects.get_for_model(step),
            object_id = step.id,
        )

        restriction.save()

        restrictions = step.taxonomic_restrictions.all()
        self.assertEqual(restrictions[0].taxon.name_uuid, lazy_taxon.name_uuid)

        
        
@test_settings
class TestDatasetImages(WithDataset, WithApp, WithUser, WithMedia, TestCase):

    test_image_filename = 'test_image.jpg'


    def create_dataset_image(self):

        dataset = self.create_dataset()

        image = SimpleUploadedFile(name=self.test_image_filename, content=open(TEST_IMAGE_PATH, 'rb').read(),
                                   content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset=dataset,
            field_uuid=uuid.uuid4(),
            image=image,
        )

        dataset_image.save()

        return dataset_image
        

    def test_user(self):

        user = self.create_user()

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS,
            created_at = timezone.now(),
            user = user,
        )

        dataset.save()

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                   content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset=dataset,
            field_uuid=uuid.uuid4(),
            image=image,
        )

        dataset_image.save()

        self.assertEqual(dataset_image.user, user)
        

    def test_get_thumb_filename(self):

        dataset_image = self.create_dataset_image()

        expected_filename = 'test_image-100.jpg'

        filename = dataset_image.get_thumb_filename()
        self.assertEqual(expected_filename, filename)

        expected_filename_400 = 'test_image-400.jpg'

        filename_400 = dataset_image.get_thumb_filename(size=400)
        self.assertEqual(expected_filename_400, filename_400)


    def test_get_thumbfolder(self):

        dataset_image = self.create_dataset_image()

        folder = dataset_image.get_thumbfolder()
        self.assertTrue(os.path.isdir(folder))

        self.assertTrue(folder.startswith(settings.MEDIA_ROOT))

    def test_get_image_format(self):

        image = Image.open(TEST_IMAGE_PATH)
        self.assertEqual(image.format, 'JPEG')

        dataset_image = self.create_dataset_image()
        image_format = dataset_image.get_image_format(image)

        self.assertEqual(image_format, 'JPEG')

    def test_thumbnail(self):

        dataset_image = self.create_dataset_image()

        # size 100
        thumbnail = dataset_image.thumbnail()
        thumbnail = thumbnail.replace('/media/', '')
        path = os.path.join(settings.MEDIA_ROOT, thumbnail)

        image = Image.open(path)
        self.assertEqual(image.size, (100,100))

        # size 200
        thumbnail_200 = dataset_image.thumbnail(size=200)
        thumbnail_200 = thumbnail_200.replace('/media/', '')
        path_200 = os.path.join(settings.MEDIA_ROOT, thumbnail_200)
        image_200 = Image.open(path_200)
        self.assertEqual(image_200.size, (200,200))


    def test_resized(self):
        # test image is 400x400

        dataset_image = self.create_dataset_image()

        size = [100,200]
        resized = dataset_image.resized('test', max_size=size)

        resized = resized.replace('/media/', '')
        path = os.path.join(settings.MEDIA_ROOT, resized)

        image = Image.open(path)
        self.assertEqual(image.size, (100,100))

        # do not upscale images
        size_2 = [500,600]
        resized_2 = dataset_image.resized('test-2', max_size=size_2)

        resized_2 = resized_2.replace('/media/', '')
        path_2 = os.path.join(settings.MEDIA_ROOT, resized_2)

        image_2 = Image.open(path_2)
        self.assertEqual(image_2.size, (400,400))
        
    
    def test_full_hd(self):

        dataset = self.create_dataset()

        image = SimpleUploadedFile(name=self.test_image_filename, content=open(LARGE_TEST_IMAGE_PATH, 'rb').read(),
                                   content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset=dataset,
            field_uuid=uuid.uuid4(),
            image=image,
        )

        dataset_image.save()


        full_hd = dataset_image.full_hd()

        full_hd = full_hd.replace('/media/', '')
        path = os.path.join(settings.MEDIA_ROOT, full_hd)

        image = Image.open(path)
        self.assertEqual(image.size, (1920, 1080))


    def test_str(self):

        dataset_image = self.create_dataset_image()

        image_text = str(dataset_image)

        self.assertEqual(image_text, 'Picea abies')
