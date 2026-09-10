from rest_framework.test import APITestCase
from rest_framework import status

from django.urls import reverse

from localcosmos_server.tests.common import test_settings, TEST_CLIENT_ID
from localcosmos_server.tests.mixins import WithApp, WithUser

from localcosmos_server.push_notifications.models import PushReceivingDevice

from fcm_django.models import FCMDevice

import uuid


TEST_REGISTRATION_ID = 'test-fcm-token-abc123'
TEST_REGISTRATION_ID_2 = 'test-fcm-token-xyz789'
TEST_CLIENT_ID_2 = str(uuid.uuid4())


class WithRegisteredDevice:

    def create_device(self, app, registration_id=TEST_REGISTRATION_ID,
                      client_id=TEST_CLIENT_ID, language_code='de'):
        fcm_device = FCMDevice.objects.create(
            registration_id=registration_id, type='android', active=True
        )
        receiving_device = PushReceivingDevice.objects.create(
            app=app, client_id=client_id, fcm_device=fcm_device, language_code=language_code
        )
        return receiving_device


class TestRegisterFCMDeviceView(WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.create_superuser()

    def get_url(self, app=None):
        return reverse('api_register_fcm_device', kwargs={'app_uuid': (app or self.app).uuid})

    def get_post_data(self, **overrides):
        data = {
            'registration_id': TEST_REGISTRATION_ID,
            'type': 'android',
            'client_id': TEST_CLIENT_ID,
            'language_code': 'de',
        }
        data.update(overrides)
        return data

    @test_settings
    def test_post_creates_device(self):
        url = self.get_url()
        response = self.client.post(url, self.get_post_data(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FCMDevice.objects.filter(registration_id=TEST_REGISTRATION_ID).exists())
        device = PushReceivingDevice.objects.get(app=self.app, client_id=TEST_CLIENT_ID)
        self.assertEqual(device.language_code, 'de')
        self.assertEqual(device.fcm_device.registration_id, TEST_REGISTRATION_ID)

    @test_settings
    def test_post_re_registration_returns_200(self):
        self.client.post(self.get_url(), self.get_post_data(), format='json')

        response = self.client.post(self.get_url(), self.get_post_data(), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @test_settings
    def test_post_updates_language_code(self):
        self.client.post(self.get_url(), self.get_post_data(language_code='de'), format='json')

        self.client.post(self.get_url(), self.get_post_data(
            registration_id=TEST_REGISTRATION_ID_2, language_code='en'
        ), format='json')

        device = PushReceivingDevice.objects.get(app=self.app, client_id=TEST_CLIENT_ID)
        self.assertEqual(device.language_code, 'en')

    @test_settings
    def test_post_token_theft_deletes_old_device(self):
        # register token on first client
        self.client.post(self.get_url(), self.get_post_data(client_id=TEST_CLIENT_ID), format='json')
        self.assertTrue(PushReceivingDevice.objects.filter(
            app=self.app, client_id=TEST_CLIENT_ID).exists())

        # same token claimed by a different client
        self.client.post(self.get_url(), self.get_post_data(client_id=TEST_CLIENT_ID_2), format='json')

        self.assertFalse(PushReceivingDevice.objects.filter(
            app=self.app, client_id=TEST_CLIENT_ID).exists())
        self.assertTrue(PushReceivingDevice.objects.filter(
            app=self.app, client_id=TEST_CLIENT_ID_2).exists())

    @test_settings
    def test_post_defaults_language_to_app_primary(self):
        data = self.get_post_data()
        data['language_code'] = ''
        self.client.post(self.get_url(), data, format='json')

        device = PushReceivingDevice.objects.get(app=self.app, client_id=TEST_CLIENT_ID)
        self.assertEqual(device.language_code, self.app.primary_language)

    @test_settings
    def test_post_invalid_app(self):
        url = reverse('api_register_fcm_device', kwargs={'app_uuid': uuid.uuid4()})
        response = self.client.post(url, self.get_post_data(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestDeregisterFCMDeviceView(WithRegisteredDevice, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.create_superuser()

    def get_url(self, app=None):
        return reverse('api_deregister_fcm_device', kwargs={'app_uuid': (app or self.app).uuid})

    @test_settings
    def test_delete(self):
        self.create_device(self.app)
        url = self.get_url()
        response = self.client.delete(url, {'client_id': TEST_CLIENT_ID}, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FCMDevice.objects.filter(registration_id=TEST_REGISTRATION_ID).exists())
        self.assertFalse(PushReceivingDevice.objects.filter(
            app=self.app, client_id=TEST_CLIENT_ID).exists())

    @test_settings
    def test_delete_device_not_found(self):
        url = self.get_url()
        response = self.client.delete(url, {'client_id': TEST_CLIENT_ID}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @test_settings
    def test_delete_invalid_app(self):
        self.create_device(self.app)
        url = reverse('api_deregister_fcm_device', kwargs={'app_uuid': uuid.uuid4()})
        response = self.client.delete(url, {'client_id': TEST_CLIENT_ID}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
