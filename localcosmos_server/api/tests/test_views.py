from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework import status

from django.urls import reverse

from localcosmos_server.tests.common import (test_settings, test_settings_commercial, TEST_CLIENT_ID, TEST_PLATFORM)
                                        
from localcosmos_server.tests.mixins import WithUser, WithObservationForm, WithApp

from rest_framework.test import APIRequestFactory, APIClient

from localcosmos_server.api.views import APIHome, RegisterAccount, TokenObtainPairViewWithClientID

from localcosmos_server.datasets.models import Dataset

from localcosmos_server.models import UserClients
from django.contrib.auth import get_user_model

User = get_user_model()

import uuid


class TestAPIHome(APITestCase):

    @test_settings
    def test_get(self):

        factory = APIRequestFactory()
        request = factory.get('/api/')
        response = APIHome.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        json_request = factory.get('/api/?format=json')
        json_response = APIHome.as_view()(json_request)
        self.assertEqual(json_response.data, {'success':True})
        self.assertEqual(json_response.status_code, 200)


class TestRegisterAccount(WithApp, WithUser, WithObservationForm, APITestCase):

    test_client_id = TEST_CLIENT_ID
    test_password = 'dfbvrthGF%/()'
    test_email = 'test@test.it'

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()


    def get_post_data(self):
        
        post_data = {
            'username' : 'TestUser',
            'password' : self.test_password,
            'password2' : self.test_password,
            'firstName' : 'Test first name',
            'lastName' : 'Test last name',
            'email' : self.test_email,
            'email2' : self.test_email,
            'clientId' : self.test_client_id,
            'platform' : TEST_PLATFORM,
            'appUuid' : str(uuid.uuid4()),
        }

        return post_data


    @test_settings
    def test_post(self):

        post_data = self.get_post_data()

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_register_account', kwargs=url_kwargs)

        json_response = self.client.post(url, post_data, format='json')

        self.assertEqual(json_response.status_code, status.HTTP_200_OK)

        self.assertEqual(json_response.data['success'], True)

        for field, value in json_response.data['user'].items():
            if field in post_data:
                self.assertEqual(value, post_data[field])

        # check if UserClients entry has been made
        user = User.objects.get(uuid=json_response.data['user']['uuid'])
        client = UserClients.objects.get(user=user)
        self.assertEqual(client.client_id, post_data['clientId'])
        self.assertEqual(client.platform, post_data['platform'])


    @test_settings
    def test_post_with_existing_anonymous_dataset(self):

        observation_form = self.create_observation_form()

        dataset = self.create_dataset(observation_form)

        self.assertEqual(dataset.user, None)

        post_data = self.get_post_data()        

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_register_account', kwargs=url_kwargs)

        json_response = self.client.post(url, post_data, format='json')

        self.assertEqual(json_response.status_code, status.HTTP_200_OK)

        self.assertEqual(json_response.data['success'], True)

        user = User.objects.get(uuid=json_response.data['user']['uuid'])

        dataset.refresh_from_db()

        self.assertEqual(dataset.user, user)


class TestTokenObtainPairViewWithClientID(WithApp, WithObservationForm, WithUser, APITestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()

    def get_user_client(self, user):
        client = UserClients.objects.filter(user=user).first()
        return client

    def get_post_data(self):

        post_data = {
            'clientId': TEST_CLIENT_ID,
            'platform': 'browser',
            'username': self.test_username,
            'password': self.test_password,
        }

        return post_data

    @test_settings
    def test_post(self):

        user = self.create_user()

        client = self.get_user_client(user)
        self.assertEqual(client, None)
        
        post_data = self.get_post_data()

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('token_obtain_pair', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        client = self.get_user_client(user)
        self.assertEqual(client.platform, post_data['platform'])
        self.assertEqual(client.user, user)
        self.assertEqual(client.client_id, post_data['clientId'])

    @test_settings
    def test_with_anonymous_dataset(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)
        self.assertEqual(dataset.user, None)

        user = self.create_user()

        client = self.get_user_client(user)
        self.assertEqual(client, None)

        post_data = self.get_post_data()


        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('token_obtain_pair', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        dataset.refresh_from_db()

        self.assertEqual(dataset.user, user)


class GetJWTokenMixin:

    def get_jw_token(self, username, password):

        post_data = {
            'clientId': TEST_CLIENT_ID,
            'platform': TEST_PLATFORM,
            'username': username,
            'password': password,
        }

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('token_obtain_pair', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        return response.data


    def get_authenticated_client(self, username, password):

        token_pair = self.get_jw_token(username, password)

        access_token = token_pair['access']

        auth_header_value = 'Bearer {0}'.format(access_token)

        authed_client = APIClient()
        authed_client.credentials(HTTP_AUTHORIZATION=auth_header_value)

        return authed_client


class TestManageAccount(GetJWTokenMixin, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()


    def get_url(self):
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_manage_account', kwargs=url_kwargs)

        return url

    @test_settings
    def test_get(self):
        
        user = self.create_user()

        url = self.get_url()

        response = self.client.get(url, format='json')

        # raises 401 unauthorized
        self.assertEqual(response.status_code, 401)

        authed_client = self.get_authenticated_client(user.username, self.test_password)

        authed_response = authed_client.get(url)

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        for key, value in authed_response.data.items():

            user_value = getattr(user, key)

            if key == 'uuid':
                user_value = str(user_value)
            self.assertEqual(value, user_value)
    

    @test_settings
    def test_put(self):
        
        user = self.create_user()

        put_data = {
            'username' : 'new_username',
            'firstName' : 'new first name',
            'lastName' : 'new last name',
            'email' : 'new@mail.email',
        }

        url = self.get_url()

        client = APIClient()
        response = client.put(url, put_data, format='json')

        # raises 401 unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        authed_client = self.get_authenticated_client(user.username, self.test_password)

        authed_response = authed_client.put(url, put_data, format='json')

        #print(authed_response.data)

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()

        self.assertEqual(user.first_name, put_data['firstName'])
        self.assertEqual(user.last_name, put_data['lastName'])
        self.assertEqual(user.email, put_data['email'])
        self.assertEqual(user.username, put_data['username'])

    @test_settings
    def test_put_400(self):

        user = self.create_user()

        url = self.get_url()

        # no email given, minium requirements are username and email
        # username contains a space, which is invalid
        put_data = {
            'username' : 'new username',
        }


        authed_client = self.get_authenticated_client(user.username, self.test_password)

        authed_response = authed_client.put(url, put_data, format='json')

        #print(authed_response.data)

        self.assertEqual(authed_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('username', authed_response.data)
        self.assertIn('email', authed_response.data)


class TestDeleteAccount(GetJWTokenMixin, WithObservationForm, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()


    def get_url(self):
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_delete_account', kwargs=url_kwargs)

        return url

    @test_settings
    def test_delete(self):

        user = self.create_user()

        user_exists = User.objects.filter(pk=user.id).exists()
        self.assertTrue(user_exists)

        url = self.get_url()

        authed_client = self.get_authenticated_client(user.username, self.test_password)
        authed_response = authed_client.delete(url, format='json')

        self.assertEqual(authed_response.status_code, status.HTTP_204_NO_CONTENT)


        user_exists = User.objects.filter(pk=user.id).exists()
        self.assertFalse(user_exists)


    @test_settings
    def test_delete_anonymize_dataset(self):

        user = self.create_user()

        url = self.get_url()

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        self.assertEqual(dataset.user, None)

        dataset.user = user
        dataset.save()
        dataset = Dataset.objects.get(pk=dataset.id)

        self.assertEqual(dataset.user, user)

        authed_client = self.get_authenticated_client(user.username, self.test_password)
        authed_response = authed_client.delete(url, format='json')

        self.assertEqual(authed_response.status_code, status.HTTP_204_NO_CONTENT)

        user_exists = User.objects.filter(pk=user.id).exists()
        self.assertFalse(user_exists)

        dataset.refresh_from_db()
        self.assertEqual(dataset.user, None)


class TestPasswordResetRequest(GetJWTokenMixin, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()

    def get_url(self):
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_password_reset', kwargs=url_kwargs)

        return url

    @test_settings
    def test_post(self):
        
        user = self.create_user()

        post_data = {
            'email' : user.email
        }

        authed_client = self.get_authenticated_client(user.username, self.test_password)
        url = self.get_url()
        authed_response = authed_client.post(url, post_data, format='json')

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        self.assertTrue(authed_response.data['success'])
    
            
    @test_settings
    def test_post_invalid(self):
        
        user = self.create_user()

        post_data = {}

        authed_client = self.get_authenticated_client(user.username, self.test_password)
        url = self.get_url()
        authed_response = authed_client.post(url, post_data, format='json')

        self.assertEqual(authed_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(authed_response.data['success'])


    @test_settings
    def test_post_no_user(self):
        
        user = self.create_user()

        post_data = {
            'email' : 'nonexistant@example.com'
        }

        authed_client = self.get_authenticated_client(user.username, self.test_password)
        url = self.get_url()
        authed_response = authed_client.post(url, post_data, format='json')

        self.assertEqual(authed_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(authed_response.data['success'])