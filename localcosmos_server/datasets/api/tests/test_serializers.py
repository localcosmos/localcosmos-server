from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from django.core.files.uploadedfile import SimpleUploadedFile

from localcosmos_server.tests.common import (test_settings, DataCreator, TEST_IMAGE_PATH, GEOJSON_POLYGON,
    TEST_USER_GEOMETRY_NAME)
from localcosmos_server.tests.mixins import WithUser, WithApp, WithObservationForm, WithMedia, WithUserGeometry
from localcosmos_server.datasets.api.serializers import (ObservationFormSerializer, DatasetSerializer,
    DatasetImagesSerializer, DatasetListSerializer, UserGeometrySerializer, DatasetRetrieveSerializer)

from localcosmos_server.datasets.models import ObservationForm, DatasetImages, Dataset, UserGeometry

from rest_framework import serializers

from django.utils import timezone

import uuid, jsonschema


class TestObservationformSerializer(WithObservationForm, TestCase):

    @test_settings
    def test_deserialize(self):

        data = {
            'definition' : self.observation_form_json
        }

        serializer = ObservationFormSerializer(data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        data = dict(serializer.validated_data)


    @test_settings
    def test_serialize(self):
        
        observation_form = self.create_observation_form()

        serializer = ObservationFormSerializer(observation_form)

        self.assertEqual(serializer.data['definition'], observation_form.definition)


    @test_settings
    def test_create(self):

        uuid = self.observation_form_json['uuid']
        version = self.observation_form_json['version']
        qry = ObservationForm.objects.filter(uuid=uuid, version=version)

        self.assertFalse(qry.exists())

        data = {
            'definition' : self.observation_form_json
        }

        serializer = ObservationFormSerializer(data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        observation_form = serializer.create(serializer.validated_data)

        self.assertTrue(qry.exists())

        self.assertEqual(observation_form.definition, self.observation_form_json)



class TestDatasetRetrieveSerializer(WithObservationForm,  WithMedia, WithApp, TestCase):

    @test_settings
    def test_serialize(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        retrieve_serializer = DatasetRetrieveSerializer(dataset)
        self.assertEqual(retrieve_serializer.data['data'], dataset.data)


class TestDatasetSerializer(WithObservationForm,  WithMedia, WithApp, TestCase):

    @test_settings
    def test_deserialize(self):
        
        data_creator = DataCreator()

        now = timezone.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S %z')

        observation_form = self.create_observation_form()

        data = {
            'observation_form' : {
                'uuid': self.observation_form_json['uuid'],
                'version': self.observation_form_json['version'],
            },
            'data' : data_creator.get_dataset_data(self.observation_form_json),
            'client_id' : 'test client',
            'platform' : 'browser',
            'created_at' : now_str,
        }

        serializer = DatasetSerializer(self.app.uuid, data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        validated_data = dict(serializer.validated_data)

        self.assertFalse('uuid' in validated_data)
        self.assertFalse('user' in validated_data)


    @test_settings
    def test_serialize(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        serializer = DatasetSerializer(self.app.uuid, dataset)

        self.assertEqual(serializer.data['data'], dataset.data)

    
    @test_settings
    def test_serialize_with_image(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)
        self.create_dataset_image(dataset)

        serializer = DatasetSerializer(self.app.uuid, dataset)

        self.assertEqual(serializer.data['data'], dataset.data)

        self.assertIn('images', serializer.data)

    @test_settings
    def test_validate(self):

        observation_form_uuid = self.observation_form_json['uuid']
        version = self.observation_form_json['version']

        data_creator = DataCreator()
        
        data = {
            'observation_form' : {
                'uuid' : observation_form_uuid,
                'version' : version,
            },
            'data': data_creator.get_dataset_data(self.observation_form_json),
        }

        qry = ObservationForm.objects.filter(uuid=observation_form_uuid, version=version)

        self.assertFalse(qry.exists())

        serializer = DatasetSerializer(self.app.uuid, data=data)

        with self.assertRaises(serializers.ValidationError):
            returned_data = serializer.validate(data)

        self.create_observation_form()

        returned_data = serializer.validate(data)
        self.assertEqual(data, returned_data)


    @test_settings
    def test_create_anonymous(self):
        
        observation_form = self.create_observation_form()

        data_creator = DataCreator()

        now = timezone.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S %z')

        data = {
            'observation_form': {
                'uuid': self.observation_form_json['uuid'],
                'version': self.observation_form_json['version'],
            },
            'data' : data_creator.get_dataset_data(self.observation_form_json),
            'client_id' : 'test client',
            'platform' : 'browser',
            'created_at' : now_str,
        }

        serializer = DatasetSerializer(self.app.uuid, data=data)

        is_valid = serializer.is_valid()

        if serializer.errors:
            print(serializer.errors)

        self.assertEqual(serializer.errors, {})

        dataset = serializer.create(serializer.validated_data)

        self.assertTrue(hasattr(dataset, 'pk'))
        self.assertIsNone(dataset.user)
        self.assertEqual(dataset.observation_form, observation_form)
        self.assertEqual(dataset.client_id, 'test client')
        self.assertEqual(dataset.platform, 'browser')


class TestDatasetImagesSerializer(WithObservationForm, WithMedia, WithApp, TestCase):

    @test_settings
    def test_serialize_and_create(self):
        
        observation_form = self.create_observation_form()

        image_field_uuid = self.get_image_field_uuid(observation_form)
        dataset = self.create_dataset(observation_form)

        qry = DatasetImages.objects.filter(dataset=dataset)
        self.assertFalse(qry.exists())

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        data = {
            'dataset': str(dataset.uuid),
            'field_uuid': image_field_uuid,
            'client_id': dataset.client_id,
            'image': image,
        }

        serializer = DatasetImagesSerializer(data=data)

        is_valid = serializer.is_valid()

        if serializer.errors:
            print(serializer.errors)
    
        self.assertEqual(serializer.errors, {})

        dataset_image = serializer.create(serializer.validated_data)

        self.assertEqual(dataset_image.dataset, dataset)

        self.assertTrue(qry.exists())


    @test_settings
    def test_deserialize(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        dataset_image = self.create_dataset_image(dataset)

        serializer = DatasetImagesSerializer(dataset_image)

        #print(serializer.data)

        self.assertEqual(serializer.data['id'], dataset_image.id)
        self.assertEqual(serializer.data['dataset'], str(dataset_image.dataset.uuid))

        for size in ['1x', '2x', '4x']:
            self.assertIn(size, serializer.data['image_url'])


class TestDatasetListSerializer(WithObservationForm, WithMedia, WithApp, TestCase):

    @test_settings
    def test_deserialize(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        dataset_image = self.create_dataset_image(dataset)

        queryset = Dataset.objects.all()

        serializer = DatasetListSerializer(queryset, many=True)

        #print(serializer.data)

        self.assertEqual(len(serializer.data), 1)

        dataset_ = serializer.data[0]

        self.assertEqual(dataset_['geographic_reference'], GEOJSON_POLYGON)

        self.assertEqual(dataset_['coordinates']['type'],'Feature')



class TestUserGeometrySerializer(WithUserGeometry, WithUser, WithApp, TestCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.user = self.create_user()

    @test_settings
    def test_serialize(self):
        
        user_geometry = self.create_user_geometry(self.user)

        serializer = UserGeometrySerializer(user_geometry)

        self.assertEqual(serializer.data['id'], user_geometry.pk)
        #self.assertEqual(serializer.data['user'], user_geometry.user.uuid)
        self.assertEqual(serializer.data['geometry'], GEOJSON_POLYGON)
        self.assertEqual(serializer.data['name'], user_geometry.name)


    @test_settings
    def test_deserialize(self):

        data = {
            'geometry': GEOJSON_POLYGON,
            'name': TEST_USER_GEOMETRY_NAME
        }

        qry = UserGeometry.objects.filter(user=self.user)

        self.assertFalse(qry.exists())

        url_kwargs = {
            'app_uuid' : str(self.app.uuid)
        }
        url = reverse('api_list_create_dataset', kwargs=url_kwargs)
        factory = APIRequestFactory()
        request = factory.post(url, data, format='json')
        request.user = self.user

        context = {
            'request' : request
        }

        serializer = UserGeometrySerializer(data=data, context=context)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        user_geometry = serializer.save()

        self.assertTrue(qry.exists())
        self.assertEqual(user_geometry, qry.first())