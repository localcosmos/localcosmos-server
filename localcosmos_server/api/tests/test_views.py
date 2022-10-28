from django.test import TestCase

from localcosmos_server.tests.common import (test_settings, test_settings_commercial,
                                        TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS, TEST_CLIENT_ID)
                                        
from localcosmos_server.tests.mixins import WithUser, WithDataset, WithApp

from rest_framework.test import APIRequestFactory, APIClient

from localcosmos_server.api.views import APIHome, RegisterAccount, TokenObtainPairViewWithClientID

from localcosmos_server.datasets.models import Dataset

from localcosmos_server.models import UserClients
from django.contrib.auth import get_user_model

User = get_user_model()

import uuid

class TestAPIHome(TestCase):

    @test_settings
    def test_get(self):

        factory = APIRequestFactory()
        request = factory.get('/api/')
        response = APIHome.as_view()(request)
        self.assertEqual(response.status_code, 200)

        json_request = factory.get('/api/?format=json')
        json_response = APIHome.as_view()(json_request)
        self.assertEqual(json_response.data, {'success':True})
        self.assertEqual(json_response.status_code, 200)


class TestRegisterAccount(WithApp, WithDataset, TestCase):

    test_client_id = TEST_CLIENT_ID
    test_password = 'dfbvrthGF%/()'
    test_email = 'test@test.it'


    def get_post_data(self):
        
        post_data = {
            'username' : 'TestUser',
            'password' : self.test_password,
            'password2' : self.test_password,
            'first_name' : 'Test first name',
            'last_name' : 'Test last name',
            'email' : self.test_email,
            'email2' : self.test_email,
            'client_id' : self.test_client_id,
            'platform' : 'browser',
            'app_uuid' : str(uuid.uuid4()),
        }

        return post_data


    @test_settings
    def test_post(self):

        post_data = self.get_post_data()        

        factory = APIRequestFactory()
        request = factory.post('/api/user/register/', post_data, format='json')

        json_response = RegisterAccount.as_view()(request)
        self.assertEqual(json_response.status_code, 200)

        self.assertEqual(json_response.data['success'], True)

        for field, value in json_response.data['user'].items():
            if field in post_data:
                self.assertEqual(value, post_data[field])

        # check if UserClients entry has been made
        user = User.objects.get(pk=json_response.data['user']['id'])
        client = UserClients.objects.get(user=user)
        self.assertEqual(client.client_id, post_data['client_id'])
        self.assertEqual(client.platform, post_data['platform'])


    @test_settings
    def test_post_with_existing_anonymous_dataset(self):

        dataset = self.create_dataset()

        self.assertEqual(dataset.user, None)

        post_data = self.get_post_data()        

        factory = APIRequestFactory()
        request = factory.post('/api/user/register/', post_data, format='json')

        json_response = RegisterAccount.as_view()(request)
        self.assertEqual(json_response.status_code, 200)

        self.assertEqual(json_response.data['success'], True)

        user = User.objects.get(pk=json_response.data['user']['id'])

        dataset.refresh_from_db()

        self.assertEqual(dataset.user, user)


class TestTokenObtainPairViewWithClientID(WithApp, WithDataset, WithUser, TestCase):

    test_client_id = TEST_CLIENT_ID

    def get_user_client(self, user):
        client = UserClients.objects.filter(user=user).first()
        return client

    def get_post_data(self):

        post_data = {
            'client_id': TEST_CLIENT_ID,
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

        factory = APIRequestFactory()
        request = factory.post('/api/token/', post_data, format='json')

        response = TokenObtainPairViewWithClientID.as_view()(request)
        self.assertEqual(response.status_code, 200)
        
        client = self.get_user_client(user)
        self.assertEqual(client.platform, post_data['platform'])
        self.assertEqual(client.user, user)
        self.assertEqual(client.client_id, post_data['client_id'])

    @test_settings
    def test_with_anonymous_dataset(self):

        dataset = self.create_dataset()
        self.assertEqual(dataset.user, None)

        user = self.create_user()

        client = self.get_user_client(user)
        self.assertEqual(client, None)

        post_data = self.get_post_data()

        factory = APIRequestFactory()
        request = factory.post('/api/token/', post_data, format='json')

        response = TokenObtainPairViewWithClientID.as_view()(request)
        self.assertEqual(response.status_code, 200)
        
        dataset.refresh_from_db()

        self.assertEqual(dataset.user, user)


class GetJWTokenMixin:

    def get_jw_token(self, username, password):

        post_data = {
            'client_id': TEST_CLIENT_ID,
            'platform': 'browser',
            'username': username,
            'password': password,
        }

        factory = APIRequestFactory()
        request = factory.post('/api/token/', post_data, format='json')

        response = TokenObtainPairViewWithClientID.as_view()(request)

        return response.data


class TestManageAccount(GetJWTokenMixin, WithUser, WithApp, TestCase):

    def get_authenticated_client(self, username, password):

        token_pair = self.get_jw_token(username, password)

        access_token = token_pair['access']

        auth_header_value = 'Bearer {0}'.format(access_token)

        authed_client = APIClient()
        authed_client.credentials(HTTP_AUTHORIZATION=auth_header_value)

        return authed_client



    @test_settings
    def test_get(self):
        
        user = self.create_user()
        superuser = self.create_superuser()

        client = APIClient()
        response = client.get('/api/user/manage/?format=json')

        # raises 401 unauthorized
        self.assertEqual(response.status_code, 401)

        authed_client = self.get_authenticated_client(user.username, self.test_password)

        authed_response = authed_client.get('/api/user/manage/?format=json')

        self.assertEqual(authed_response.status_code, 200)

        for key, value in authed_response.data['user'].items():

            user_value = getattr(user, key)

            if key == 'uuid':
                user_value = str(user_value)
            self.assertEqual(value, user_value)
    

    @test_settings
    def test_put(self):
        
        user = self.create_user()
        superuser = self.create_superuser()

        put_data = {
            'username' : 'new_username',
            'first_name' : 'new first name',
            'last_name' : 'new last name',
            'email' : 'new@mail.email',
        }

        client = APIClient()
        response = client.put('/api/user/manage/', put_data, format='json')

        # raises 401 unauthorized
        self.assertEqual(response.status_code, 401)

        authed_client = self.get_authenticated_client(user.username, self.test_password)

        authed_response = authed_client.put('/api/user/manage/', put_data, format='json')

        #print(authed_response.data)

        self.assertEqual(authed_response.status_code, 200)
        self.assertTrue(authed_response.data['success'])


        for key, value in authed_response.data['user'].items():

            if key in put_data:
                self.assertEqual(value, put_data[key])

    @test_settings
    def test_put_400(self):

        user = self.create_user()
        superuser = self.create_superuser()

        put_data = {
            'username' : 'new username',
        }


        authed_client = self.get_authenticated_client(user.username, self.test_password)

        authed_response = authed_client.put('/api/user/manage/', put_data, format='json')

        #print(authed_response.data)

        self.assertEqual(authed_response.status_code, 400)

        self.assertFalse(authed_response.data['success'])
        self.assertIn('errors', authed_response.data)



class TestPasswordResetRequest(TestCase):

    @test_settings
    def test_get(self):
        pass

    @test_settings
    def test_post(self):
        pass