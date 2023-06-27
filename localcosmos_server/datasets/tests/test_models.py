###################################################################################################################
#
# TESTS FOR MODELS
# - this file only covers settings.LOCALCOSMOS_PRIVATE == True
#
###################################################################################################################
from django.conf import settings
from django.test import TestCase
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import Point, Polygon, GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _


from localcosmos_server.datasets.models import (Dataset, DatasetValidationRoutine, DatasetImages, IMAGE_SIZES,
    DATASET_VALIDATION_CHOICES, DATASET_VALIDATION_DICT, UserGeometry)

from localcosmos_server.models import UserClients, TaxonomicRestriction

from localcosmos_server.tests.common import (test_settings, TEST_IMAGE_PATH, TEST_CLIENT_ID, TEST_PLATFORM,
    TEST_TIMESTAMP_OFFSET, TEST_LATITUDE, TEST_LONGITUDE, LARGE_TEST_IMAGE_PATH, DataCreator, TEST_TIMESTAMP,
    GEOJSON_POLYGON)

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithObservationForm
from localcosmos_server.utils import timestamp_from_utc_with_offset

from PIL import Image

import uuid, os, json


mercator_srid = SpatialReference(4326)
database_srid = SpatialReference(3857)
trans_4326_to_3857 = CoordTransform(mercator_srid, database_srid)


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



class TestDataset(WithValidationRoutine, WithObservationForm, WithApp, WithUser, TestCase):


    def get_test_data(self, observation_form_json):
        data_creator = DataCreator()
        test_data = data_creator.get_dataset_data(self.observation_form_json)
        return test_data


    # this also tests update_redundant_columns
    @test_settings
    def test_save_without_validation_routine(self):

        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form=observation_form)

        test_data = self.get_test_data(self.observation_form_point_json)

        # fetch the dataset to perform coordinate transformation
        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertTrue(dataset.is_valid)
        self.assertEqual(dataset.data, test_data)
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

        self.assertEqual(dataset.coordinates, dataset.geographic_reference)
        
        self.assertEqual(dataset.app_uuid, self.app.uuid)

        self.assertEqual(dataset.user, None)
        self.assertEqual(dataset.validation_errors, None)


    # in this case, the first (and only) validation step is a human interaction step
    # if it were an automatic step, the test would have to be different
    @test_settings
    def test_save_with_validation_routine(self):

        self.create_validation_routine()
        observation_form = self.create_observation_form()

        dataset = self.create_dataset(observation_form)

        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertFalse(dataset.is_valid)
        self.assertEqual(dataset.validation_step, DATASET_VALIDATION_CHOICES[0][0])
        

    @test_settings
    def test_save_with_user(self):

        user = self.create_user()

        client_link = UserClients(
            user = user,
            client_id = TEST_CLIENT_ID,
            platform = TEST_PLATFORM,
        )

        client_link.save()

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        # fetch the dataset to perform coordinate transformation
        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertEqual(dataset.user, user)
        

    @test_settings
    def test_validation_routine(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        self.assertEqual(dataset.validation_routine.count(), 0)
        
        # test with existing validation_routine
        self.create_validation_routine()

        dataset_2 = self.create_dataset(observation_form)

        self.assertEqual(dataset_2.validation_routine.count(), len(DATASET_VALIDATION_CHOICES))


    # this is currently covered by test_save, as Dataset.save() triggers Dataset.validate()
    @test_settings
    def test_validate(self):
        pass

    @test_settings
    def test_current_validation_status(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        self.assertEqual(dataset.current_validation_status, 'completed')
        
        # test with existing validation_routine
        self.create_validation_routine()

        dataset_2 = self.create_dataset(observation_form)

        step = DATASET_VALIDATION_DICT[DATASET_VALIDATION_CHOICES[0][0]]

        self.assertEqual(dataset_2.current_validation_status, step.status_message)
        

    @test_settings
    def test_current_validation_step(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        self.assertEqual(dataset.current_validation_step, None)
        
        # test with existing validation_routine
        self.create_validation_routine()

        dataset_2 = self.create_dataset(observation_form)

        first_step = DatasetValidationRoutine.objects.filter(app=self.app).order_by('position').first()
        
        self.assertEqual(dataset_2.current_validation_step, first_step)
        

    @test_settings
    def test_use_existing_client_id(self):

        # but the dataset contains an unknown client_id AND the platform is the browser
        observation_form = self.create_observation_form(self.observation_form_json)

        user = self.create_user()

        existing_client_id = 'existing_client_id'

        client_link = UserClients(
            user = user,
            client_id = existing_client_id,
            platform = TEST_PLATFORM,
        )

        client_link.save()

        test_data = self.get_test_data(self.observation_form_json)

        dataset = Dataset(
            app_uuid = self.app.uuid,
            observation_form = observation_form,
            data = test_data,
            client_id = existing_client_id,
            platform = TEST_PLATFORM,
            user = user,
        )

        dataset.save()

        dataset = Dataset.objects.get(pk=dataset.pk)

        self.assertEqual(dataset.client_id, existing_client_id)
        self.assertTrue(dataset.created_at is not None)
    
    # test the following:
    # dataset .client_id, .user, .coordinates, .geographic_reference , .timestamp
    @test_settings
    def test_update_redundant_columns(self):    

        # tests for update_redundant_columns if the dataset is created are covered by test_save()
        # the following tests are for the case if a dataset is being updated

        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)

        dataset = Dataset.objects.get(pk=dataset.pk)

        # alter all test data
        test_data = self.get_test_data(self.observation_form_json)

        altered_timestamp = 1576161198595

        altered_latitude = TEST_LATITUDE + 1
        altered_longitude = TEST_LONGITUDE + 1

        altered_taxon_nuid = "006002009001005005002"
        altered_name_uuid = "77380de8-8087-41b4-9577-67b929593b0b"
        altered_taxon_source = "taxonomy.sources.col"
        altered_taxon_latname =  "Larix decidua"
        altered_taxon_author = "Linnaeus 12345"



        alterations = {}

        alterations[self.observation_form_point_json['temporalReference']] = {
            "cron": {
                "type": "timestamp",
                "format": "unixtime",
                "timestamp": altered_timestamp,
                "timezoneOffset": TEST_TIMESTAMP_OFFSET
            },
            "type": "Temporal"
        }

        alterations[self.observation_form_point_json['taxonomicReference']] = {
            "taxonNuid": altered_taxon_nuid,
            "nameUuid": altered_name_uuid,
            "taxonSource": altered_taxon_source,
            "taxonLatname": altered_taxon_latname,
            "taxonAuthor" : altered_taxon_author,
        }

        alterations[self.observation_form_point_json['geographicReference']] = {
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
            
        

        for key, value in alterations.items():

            test_data[key] = value

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


    @test_settings
    def test_update_redundant_columns_polygon(self):
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_json)
        dataset = self.create_dataset(observation_form)

        dataset = Dataset.objects.get(pk=dataset.pk)      
        self.assertTrue(isinstance(dataset.coordinates, Point))
        self.assertTrue(isinstance(dataset.geographic_reference, Polygon))


    @test_settings
    def test_nearby(self):

        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)

        dataset = self.create_dataset(observation_form)
        user = self.create_user()

        test_data = self.get_test_data(self.observation_form_point_json)

        dataset_2 = Dataset(
            app_uuid = self.app.uuid,
            observation_form=observation_form,
            data = test_data,
            client_id = TEST_CLIENT_ID,
            platform = TEST_PLATFORM,
            user = user,
        )

        dataset_2.save()

        dataset = Dataset.objects.get(pk=dataset.pk)

        nearby = dataset.nearby()

        self.assertEqual(len(nearby), 1)

        nearby_dataset = nearby[0]
        self.assertEqual(nearby_dataset.pk, dataset_2.pk)
        self.assertEqual(nearby_dataset.user, user)


    @test_settings
    def test_validate_requirements(self):

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = None,
        )

        with self.assertRaises(ValueError):
            dataset.validate_requirements()


        dataset.data = {}

        with self.assertRaises(ValueError):
            dataset.validate_requirements()

        
        dataset.data = {
            'uuid': 'value'
        }

        dataset.validate_requirements()


        
    @test_settings
    def test_str(self):
        # test with and without taxon_latname
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        self.assertEqual(str(dataset), 'Picea abies')

        test_data = self.get_test_data(self.observation_form_json)
        # delete the taxon

        taxon_field_uuid = observation_form.definition['taxonomicReference']
        del test_data[taxon_field_uuid]

        dataset = Dataset(
            app_uuid = self.app.uuid,
            observation_form = observation_form,
            data = test_data,
            client_id = TEST_CLIENT_ID,
            platform = TEST_PLATFORM,
        )

        dataset.save()

        self.assertEqual(str(dataset), str(_('Unidentified')))


class TestDatasetWithMedia(WithMedia, WithObservationForm, WithApp, WithUser, TestCase):

    @test_settings
    def test_thumbnail(self):

        # first, test dataset without images
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        dataset = Dataset.objects.get(pk=dataset.pk)

        thumbnail = dataset.thumbnail
        self.assertEqual(thumbnail, None)

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset=dataset,
            field_uuid=uuid.uuid4(),
            image=image,
        )

        dataset_image.save()

        thumbnail = dataset.thumbnail
        self.assertTrue(thumbnail.endswith('.jpg'))

        sized_url = dataset_image.get_image_url(250, square=True)
        sized = sized_url.replace('/media/', '')
        path = os.path.join(settings.MEDIA_ROOT, sized)
        image = Image.open(path)
        self.assertEqual(image.size, (250, 250))
    

from localcosmos_server.datasets.validation.base import DatasetValidatorBase
from localcosmos_server.taxonomy.lazy import LazyAppTaxon

class TestDatasetValidationRoutine(WithValidationRoutine, WithApp, TestCase):

    @test_settings
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
            
    @test_settings
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

        
        

class TestDatasetImages(WithObservationForm, WithApp, WithUser, WithMedia, TestCase):

    test_image_filename = 'test_image.jpg'
        
    @test_settings
    def test_user_client_id_app_uuid(self):

        user = self.create_user()

        observation_form=self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset.user = user
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
        self.assertEqual(dataset_image.client_id, TEST_CLIENT_ID)
        self.assertEqual(dataset_image.app_uuid, self.app.uuid)


    @test_settings
    def test_resized_folder(self):

        observation_form=self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset)

        folder = dataset_image.resized_folder
        self.assertTrue(os.path.isdir(folder))

        self.assertTrue(folder.startswith(settings.MEDIA_ROOT))

        

    @test_settings
    def test_get_resized_filename(self):

        observation_form=self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset)

        for size in [250, 500]:

            expected_filename = 'test_image-{0}.jpg'.format(size)

            filename = dataset_image.get_resized_filename(size)
            self.assertEqual(expected_filename, filename)

            expected_square_filename = 'test_image-{0}-square.jpg'.format(size)

            square_filename = dataset_image.get_resized_filename(size, square=True)
            self.assertEqual(expected_square_filename, square_filename)


    @test_settings
    def test_get_image_url(self):

        observation_form=self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset, image_path=LARGE_TEST_IMAGE_PATH)

        for size in [250, 500]:

            sized_url = dataset_image.get_image_url(size)
            sized = sized_url.replace('/media/', '')
            path = os.path.join(settings.MEDIA_ROOT, sized)

            image = Image.open(path)
            self.assertEqual(max(image.size), size)

            square_sized_url = dataset_image.get_image_url(size, square=True)
            square_sized = square_sized_url.replace('/media/', '')
            path = os.path.join(settings.MEDIA_ROOT, square_sized)

            square_image = Image.open(path)
            self.assertEqual(square_image.size, (size, size))



    @test_settings
    def test_image_urls(self):
        
        observation_form=self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset, image_path=LARGE_TEST_IMAGE_PATH)

        image_urls = dataset_image.image_urls

        for size_name, image_size in IMAGE_SIZES['all'].items():
            self.assertIn(size_name, image_urls)


    @test_settings
    def test_str(self):

        observation_form=self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset, image_path=LARGE_TEST_IMAGE_PATH)

        image_text = str(dataset_image)

        self.assertEqual(image_text, 'Picea abies')


class TestUserGeometry(WithUser, TestCase):

    @test_settings
    def test_create_get(self):

        user = self.create_user()

        geojson = json.dumps(GEOJSON_POLYGON['geometry'])
        geos_geometry = GEOSGeometry(geojson, srid=4326)

        name = 'Test name'

        user_geometry = UserGeometry(
            user=user,
            geometry=geos_geometry,
            name=name,
        )

        user_geometry.save()

        geom_qry = UserGeometry.objects.filter(user=user)
        self.assertEqual(geom_qry.first(), user_geometry)