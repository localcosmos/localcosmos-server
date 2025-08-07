from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework import status

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from localcosmos_server.tests.common import (test_settings, test_settings_app_kit, TEST_CLIENT_ID, TEST_PLATFORM,
     TEST_IMAGE_PATH, LARGE_TEST_IMAGE_PATH)                               
from localcosmos_server.tests.mixins import WithMedia, WithUser, WithObservationForm, WithApp, WithServerContentImage

from rest_framework.test import APIRequestFactory, APIClient

from localcosmos_server.api.views import APIHome, RegisterAccount, TokenObtainPairViewWithClientID

from djangorestframework_camel_case.util import underscoreize

from localcosmos_server.datasets.models import Dataset

from localcosmos_server.models import UserClients, ServerImageStore
from django.contrib.auth import get_user_model

import json

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

        response_data = json.loads(json_response.content)

        self.assertIn('firstName', response_data['user'])

        self.assertEqual(response_data['success'], True)

        self.assertEqual(underscoreize(response_data), json_response.data)

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


    @test_settings
    def test_register_without_name(self):

        post_data = self.get_post_data()
        del post_data['firstName']
        del post_data['lastName']

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_register_account', kwargs=url_kwargs)

        json_response = self.client.post(url, post_data, format='json')

        self.assertEqual(json_response.status_code, status.HTTP_200_OK)

        user = User.objects.get(uuid=json_response.data['user']['uuid'])

        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
    

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

        response_data = json.loads(authed_response.content)
        self.assertIn('firstName', response_data)
        self.assertEqual(underscoreize(response_data), authed_response.data)

        for key, value in authed_response.data.items():

            if key == 'profile_picture':
                continue

            user_value = getattr(user, key)

            if key == 'uuid':
                user_value = str(user_value)
            self.assertEqual(value, user_value)
    

    @test_settings
    def test_put(self):
        
        user = self.create_user()
        
        # currently, username is a read only field

        put_data = {
            #'username' : 'new_username',
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
        #self.assertEqual(user.username, put_data['username'])

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

        # currently, username is read only
        #self.assertIn('username', authed_response.data)
        self.assertIn('email', authed_response.data)


class TestDeleteAccount(GetJWTokenMixin, WithObservationForm, WithUser, WithApp, APITestCase):

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


class TestManageServerContentImage(WithServerContentImage, GetJWTokenMixin, WithMedia, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'model': 'LocalcosmosUser',
            'object_id': self.user.id,
            'image_type': 'profilepicture',
        }

        return url_kwargs


    @test_settings
    def test_get_content_image_no_image(self):

        # test generic get
        get_url_kwargs = self.get_url_kwargs()

        url = reverse('api_server_content_image', kwargs=get_url_kwargs)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # test with content image pk
        pk_get_url_kwargs = {
            'app_uuid' : self.app.uuid,
            'pk': 1
        }

        url = reverse('api_server_content_image', kwargs=pk_get_url_kwargs)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @test_settings
    def test_get(self):

        content_image = self.get_content_image(self.user, self.user, image_type='profilepicture')

        get_url_kwargs = self.get_url_kwargs()

        url = reverse('api_server_content_image', kwargs=get_url_kwargs)

        response = self.client.get(url, **get_url_kwargs)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        parsed_response = json.loads(response.content)

        media_path = '/media/localcosmos-server/imagestore/{0}/thumbnails/a6a11b61d65ee19c4c22caa0682288ff-uncropped-nofeatures-'.format(
            self.user.id)

        expected_response = {
            "id": content_image.id,
            "imageUrl":{
                "1x":"{0}200.jpg".format(media_path),
                "2x":"{0}400.jpg".format(media_path),
            }
        }

        self.assertEqual(parsed_response, expected_response)

        # pk

        pk_get_url_kwargs = {
            'app_uuid' : self.app.uuid,
            'pk': content_image.pk
        }

        url = reverse('api_server_content_image', kwargs=pk_get_url_kwargs)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_response)


    @test_settings
    def test_get_wrong_model_name(self):

        get_url_kwargs = {
            'app_uuid' : self.app.uuid,
            'model': 'LocalcosmosUserWrong',
            'object_id': self.user.id,
            'image_type': 'profilepicture',
        }

        url = reverse('api_server_content_image', kwargs=get_url_kwargs)

        response = self.client.get(url, **get_url_kwargs)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def get_post_data(self, override_data={}):

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')
        data = {
            'sourceImage' : image,
            'cropParameters' : '',
        }

        data.update(override_data)

        return data

    @test_settings
    def test_post(self):

        post_data = self.get_post_data()

        post_url_kwargs = self.get_url_kwargs()
        url = reverse('api_server_content_image', kwargs=post_url_kwargs)

        image = self.user.image('profilepicture')
        self.assertEqual(image, None)

        # mutlipart, json format cant upload files. Json data comes as string and has to be parsed
        response = self.client.post(url, post_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        authed_client = self.get_authenticated_client(self.user.username, self.test_password)

        post_data = self.get_post_data()
        authed_response = authed_client.post(url, post_data, format='multipart')

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        parsed_response = json.loads(authed_response.content)

        image = self.user.image('profilepicture')

        media_path = '/media/localcosmos-server/imagestore/{0}/thumbnails/a6a11b61d65ee19c4c22caa0682288ff-uncropped-nofeatures-'.format(
            self.user.id)

        expected_response = {
            "id": image.id,
            "imageUrl":{
                "1x":"{0}200.jpg".format(media_path),
                "2x":"{0}400.jpg".format(media_path),
            }
        }

        self.assertEqual(parsed_response, expected_response)

    @test_settings
    def test_post_crop_parameters(self):

        self.clean_media()

        crop_parameters = {
            'x': 1,
            'y': 2,
            'width': 3,
            'height': 4,
        }

        override_data = {
            'cropParameters' : json.dumps(crop_parameters),
        }
        
        post_data = self.get_post_data(override_data=override_data)

        post_url_kwargs = self.get_url_kwargs()
        url = reverse('api_server_content_image', kwargs=post_url_kwargs)

        authed_client = self.get_authenticated_client(self.user.username, self.test_password)

        authed_response = authed_client.post(url, post_data, format='multipart')

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        parsed_response = json.loads(authed_response.content)

        self.user.refresh_from_db()
        image = self.user.image('profilepicture')

        self.assertEqual(image.crop_parameters, json.dumps(crop_parameters))

        media_path = '/media/localcosmos-server/imagestore/{0}/thumbnails/a6a11b61d65ee19c4c22caa0682288ff-dffbde21fc7c45cf16aa73eddcf7f8cd-nofeatures-'.format(
            self.user.id)

        expected_response = {
            "id": image.id,
            "imageUrl":{
                "1x":"{0}200.jpg".format(media_path),
                "2x":"{0}400.jpg".format(media_path),
            }
        }

        self.assertEqual(parsed_response, expected_response)


    @test_settings
    def test_put(self):
        
        content_image = self.get_content_image(self.user, self.user, image_type='profilepicture')
        old_image_store = content_image.image_store
        qry = ServerImageStore.objects.filter(pk=old_image_store.pk)
        image = self.user.image('profilepicture')
        self.assertEqual(image, content_image)

        put_image = SimpleUploadedFile(name='test_image.jpg', content=open(LARGE_TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')
        put_data = {
            'sourceImage' : put_image,
            'cropParameters' : '',
        }

        put_url_kwargs = self.get_url_kwargs()

        url = reverse('api_server_content_image', kwargs=put_url_kwargs)
        response = self.client.put(url, put_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertTrue(qry.exists())

        put_image.seek(0)
        authed_client = self.get_authenticated_client(self.user.username, self.test_password)
        authed_response = authed_client.put(url, put_data, format='multipart')

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        parsed_response = json.loads(authed_response.content)

        media_path = '/media/localcosmos-server/imagestore/{0}/thumbnails/0793e1a469f8480283516bd8e545db79-uncropped-nofeatures-'.format(
            self.user.id)

        expected_response = {
            "id": image.id,
            "imageUrl":{
                "1x":"{0}200.jpg".format(media_path),
                "2x":"{0}400.jpg".format(media_path),
            }
        }

        self.assertEqual(parsed_response, expected_response)

        self.assertFalse(qry.exists())


    @test_settings
    def test_delete(self):
        
        content_image = self.get_content_image(self.user, self.user, image_type='profilepicture')
        old_image_store = content_image.image_store
        qry = ServerImageStore.objects.filter(pk=old_image_store.pk)

        image = self.user.image('profilepicture')
        self.assertEqual(image, content_image)

        delete_url_kwargs = {
            'app_uuid': self.app.uuid,
            'pk': content_image.pk,
        }

        url = reverse('api_server_content_image', kwargs=delete_url_kwargs)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        authed_client = self.get_authenticated_client(self.user.username, self.test_password)
        authed_response = authed_client.delete(url)

        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)

        self.assertFalse(qry.exists())

        image = self.user.image('profilepicture')
        self.assertEqual(image, None)
        

class TestGetUserProfile(WithUser, WithApp, APITestCase):

    @test_settings
    def test_get(self):

        user = self.create_user()
        su = self.create_superuser()

        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'uuid': str(user.uuid)
        }
        url = reverse('api_get_user_profile', kwargs=url_kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        expected_content = {
            'uuid': str(user.uuid),
            'username': user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'profilePicture': None,
            'dateJoined': user.date_joined.strftime('%Y-%m-%dT%H:%M:%S.%fZ'), # '2023-12-15T13:20:30.210506Z'
            'datasetCount': 0,
        }
        self.assertEqual(json.loads(response.content), expected_content)



class TestContactUser(GetJWTokenMixin, WithUser, WithApp, APITestCase):
    
    @test_settings
    def test_post(self):
        
        sender = self.create_user()
        receiver = self.create_superuser()
        
        
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'user_uuid': str(receiver.uuid)
        }        
        url = reverse('api_contact_user', kwargs=url_kwargs)
        
        post_data  = {
            'subject': 'Hello User',
            'message': 'This is a nice message to you. Have fun.'
        }
        response = self.client.post(url, post_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        authed_client = self.get_authenticated_client(sender.username, self.test_password)
        authed_response = authed_client.post(url, post_data, format='json')
        
        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)


class TestTaxonProfileDetail(GetJWTokenMixin, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        su = self.create_superuser()
        self.authed_client = self.get_authenticated_client(self.user.username, self.test_password)
        self.test_pk = 1
        self.test_taxon = {
            "taxon_source": "taxonomy.sources.col",
            "name_uuid": "01ad3dc7-e744-499f-9097-abb4760fdbc4"
        }
        
        self.app.url = 'http://testserver'
        self.app.save()

    @test_settings
    def test_get_taxon_profile_detail_404(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'pk': 9999  # Nonexistent pk
        }
        url = reverse('api_taxon_profile', kwargs=url_kwargs)
        response = self.authed_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @test_settings
    def test_get_taxon_profile_detail_success(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'pk': self.test_pk
        }
        url = reverse('api_taxon_profile', kwargs=url_kwargs)
        response = self.authed_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nameUuid'], self.test_taxon['name_uuid'])


class TestTaxonProfileList(GetJWTokenMixin, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        su = self.create_superuser()
        self.authed_client = self.get_authenticated_client(self.user.username, self.test_password)
        self.app.url = 'http://testserver'
        self.app.save()

    @test_settings
    def test_get_taxon_profile_list_success(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
        }
        url = reverse('api_taxon_profile_list', kwargs=url_kwargs)
        response = self.authed_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)
        # Optionally check for expected fields in the first result if any exist
        if response.data['results']:
            first_profile = response.data['results'][0]
            self.assertIn('nameUuid', first_profile)
            self.assertIn('taxonLatname', first_profile)



class TestAllTaxonProfiles(GetJWTokenMixin, WithUser, WithApp, APITestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        su = self.create_superuser()
        self.authed_client = self.get_authenticated_client(self.user.username, self.test_password)
        self.app.url = 'http://testserver'
        self.app.save()

    @test_settings
    def test_get_taxon_profile_list_success(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
        }
        url = reverse('api_all_taxon_profiles', kwargs=url_kwargs)
        response = self.authed_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_respoinse = [
            {
                'taxonProfileId': 1,
                'taxonLatname': 'Abies alba',
                'taxonAuthor': 'Mill.',
                'vernacular': {
                    'de': 'Weisstanne'
                }
            }
        ]

        self.assertEqual(response.data, expected_respoinse)
