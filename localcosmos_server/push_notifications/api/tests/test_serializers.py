from django.test import TestCase

from localcosmos_server.tests.common import test_settings, TEST_CLIENT_ID

from localcosmos_server.push_notifications.api.serializers import (
    RegisterFCMDeviceSerializer,
    DeregisterFCMDeviceSerializer,
)


class TestRegisterFCMDeviceSerializer(TestCase):

    def get_valid_data(self):
        return {
            'registration_id': 'test-fcm-token-abc123',
            'type': 'android',
            'client_id': TEST_CLIENT_ID,
            'language_code': 'de',
        }

    @test_settings
    def test_valid_data(self):
        serializer = RegisterFCMDeviceSerializer(data=self.get_valid_data())
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data['language_code'], 'de')

    @test_settings
    def test_language_code_defaults_to_empty(self):
        data = self.get_valid_data()
        del data['language_code']
        serializer = RegisterFCMDeviceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['language_code'], '')

    @test_settings
    def test_language_code_allows_blank(self):
        data = self.get_valid_data()
        data['language_code'] = ''
        serializer = RegisterFCMDeviceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['language_code'], '')

    @test_settings
    def test_invalid_device_type(self):
        data = self.get_valid_data()
        data['type'] = 'windows'
        serializer = RegisterFCMDeviceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('type', serializer.errors)

    @test_settings
    def test_missing_registration_id(self):
        data = self.get_valid_data()
        del data['registration_id']
        serializer = RegisterFCMDeviceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('registration_id', serializer.errors)


class TestDeregisterFCMDeviceSerializer(TestCase):

    @test_settings
    def test_valid_data(self):
        serializer = DeregisterFCMDeviceSerializer(data={'client_id': TEST_CLIENT_ID})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['client_id'], TEST_CLIENT_ID)

    @test_settings
    def test_missing_client_id(self):
        serializer = DeregisterFCMDeviceSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('client_id', serializer.errors)
