from django.test import TestCase

from django.core.files.uploadedfile import SimpleUploadedFile

from localcosmos_server.tests.common import test_settings, DataCreator, TEST_IMAGE_PATH
from localcosmos_server.tests.mixins import WithApp, WithObservationForm, WithMedia

from localcosmos_server.datasets.api.serializers import (ObservationFormSerializer, DatasetSerializer,
    DatasetImagesSerializer, DatasetListSerializer)

from localcosmos_server.datasets.models import ObservationForm, DatasetImages, Dataset

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


class TestDatasetSerializer(WithObservationForm, WithApp, TestCase):

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
            'dataset': dataset.pk,
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
        self.assertEqual(serializer.data['dataset']['id'], dataset_image.dataset.id)

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
