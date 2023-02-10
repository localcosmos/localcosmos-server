from django.test import TestCase

from localcosmos_server.tests.common import test_settings, DataCreator
from localcosmos_server.tests.mixins import WithApp

from localcosmos_server.datasets.api.serializers import ObservationFormSerializer, DatasetSerializer

from .mixins import WithObservationForm

from localcosmos_server.datasets.models import ObservationForm

from rest_framework import serializers

from django.utils import timezone

import uuid


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

        self.assertEqual(serializer.data, observation_form.definition)


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
            'observation_form_uuid' : self.observation_form_json['uuid'],
            'observation_form_version' : self.observation_form_json['version'],
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
        
        data = {
            'observation_form' : {
                'uuid' : observation_form_uuid,
                'version' : version,
            }
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
            'observation_form_uuid' : self.observation_form_json['uuid'],
            'observation_form_version' : self.observation_form_json['version'],
            'data' : data_creator.get_dataset_data(self.observation_form_json),
            'client_id' : 'test client',
            'platform' : 'browser',
            'created_at' : now_str,
        }

        serializer = DatasetSerializer(self.app.uuid, data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        dataset = serializer.create(serializer.validated_data)

        self.assertTrue(hasattr(dataset, 'pk'))
        self.assertIsNone(dataset.user)
        self.assertEqual(dataset.observation_form, observation_form)
        self.assertEqual(dataset.client_id, 'test client')
        self.assertEqual(dataset.platform, 'browser')




