from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from django.urls import reverse

from localcosmos_server.tests.common import (test_settings, DataCreator, TEST_IMAGE_PATH, TEST_CLIENT_ID, TEST_PLATFORM,
    GEOJSON_POLYGON, TEST_USER_GEOMETRY_NAME, TEST_TAXA)
from localcosmos_server.tests.mixins import WithUser, WithApp, WithObservationForm, WithMedia, WithUserGeometry

from localcosmos_server.datasets.models import ObservationForm, Dataset, DatasetImages

from django.utils import timezone

import json


class CreatedUsersMixin:

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.user = self.create_user()

class TestCreateObservationForm(WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):

    @test_settings
    def test_post(self):

        uuid = self.observation_form_json['uuid']
        version = self.observation_form_json['version']
        qry = ObservationForm.objects.filter(uuid=uuid, version=version)

        self.assertFalse(qry.exists())

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_create_observation_form', kwargs=url_kwargs)

        post_data = {
            'definition' : self.observation_form_json
        }

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # log in
        self.client.force_authenticate(user=self.user)

        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())


    @test_settings
    def test_post_anonymous_observations(self):

        uuid = self.observation_form_json['uuid']
        version = self.observation_form_json['version']
        qry = ObservationForm.objects.filter(uuid=uuid, version=version)

        self.assertFalse(qry.exists())
    

        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
        }

        url = reverse('api_create_observation_form', kwargs=url_kwargs)

        post_data = {
            'definition' : self.observation_form_json
        }

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())



class TestRetrieveObservationForm(WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):

    @test_settings
    def test_get(self):
        
        observation_form = self.create_observation_form()

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'observation_form_uuid' : self.observation_form_json['uuid'],
            'version' : self.observation_form_json['version']
        }

        url = reverse('api_retrieve_observation_form', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # log in
        self.client.force_authenticate(user=self.user)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['definition'], self.observation_form_json)


    @test_settings
    def test_get_anonymous_observations(self):
        
        observation_form = self.create_observation_form()

        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'observation_form_uuid' : self.observation_form_json['uuid'],
            'version' : self.observation_form_json['version']
        }

        url = reverse('api_retrieve_observation_form', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['definition'], self.observation_form_json)


    @test_settings
    def test_get_fail(self):
        
        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'observation_form_uuid' : self.observation_form_json['uuid'],
            'version' : self.observation_form_json['version']
        }

        url = reverse('api_retrieve_observation_form', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



class WithDatasetPostData:

    def get_post_data(self, alternative_data=False):

        data_creator = DataCreator()

        dataset_data = data_creator.get_dataset_data(self.observation_form_json, alternative_data=alternative_data)

        now = timezone.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S %z')

        post_data = {
            'observation_form' : {
                'uuid': self.observation_form_json['uuid'],
                'version': self.observation_form_json['version'],
            },  
            'data' : dataset_data,
            'clientId' : TEST_CLIENT_ID,
            'platform' : TEST_PLATFORM,
            'createdAt' : now_str,
        }

        return post_data



class TestListCreateDataset(WithDatasetPostData, WithObservationForm, WithMedia, WithUser, WithApp, CreatedUsersMixin,
    APITestCase):


    @test_settings
    def test_post(self):
        
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_list_create_dataset', kwargs=url_kwargs)

        post_data = self.get_post_data()

        qry = Dataset.objects.all()

        self.assertFalse(qry.exists())

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # log in
        self.client.force_authenticate(user=self.user)

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.create_observation_form()

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())

        dataset = qry.first()
        self.assertEqual(dataset.user, self.user)


    @test_settings
    def test_post_ao(self):
        
        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
        }

        url = reverse('api_list_create_dataset', kwargs=url_kwargs)

        post_data = self.get_post_data()

        qry = Dataset.objects.all()

        self.assertFalse(qry.exists())

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.create_observation_form()

        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())

        dataset = qry.first()
        self.assertIsNone(dataset.user)


    @test_settings
    def test_post_ao_no_created_at(self):

        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
        }

        url = reverse('api_list_create_dataset', kwargs=url_kwargs)

        post_data = self.get_post_data()
        del post_data['createdAt']

        qry = Dataset.objects.all()

        self.assertFalse(qry.exists())
        
        self.create_observation_form()

        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())

        dataset = qry.first()
        self.assertIsNone(dataset.user)


    @test_settings
    def test_get_list_registered(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset.user = self.user
        dataset.save()
        dataset_image = self.create_dataset_image(dataset)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_list_create_dataset', kwargs=url_kwargs)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        #print(response.data)
        _dataset = response.data['results'][0]

        self.assertEqual(_dataset['uuid'], str(dataset.uuid))


    @test_settings
    def test_get_list_anonymous(self):
    
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_list_create_dataset', kwargs=url_kwargs)

        url_with_client_id = '{0}?client_id={1}'.format(url, dataset.client_id)        

        response = self.client.get(url_with_client_id, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        #print(response.data)
        _dataset = response.data['results'][0]
        self.assertEqual(_dataset['uuid'], str(dataset.uuid))

        # retrieves all datasets
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


        dataset.user = self.user
        dataset.client_id = 'another client'
        dataset.save()

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    @test_settings
    def test_get_list_all_datasets(self):
    
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_list_create_dataset', kwargs=url_kwargs)

        # retrieves all datasets
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        #print(response.data)
        _dataset = response.data['results'][0]
        self.assertEqual(_dataset['uuid'], str(dataset.uuid))



class TestRetrieveDataset(WithDatasetPostData, WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):
    
    @test_settings
    def test_get(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['uuid'], str(dataset.uuid))



class TestUpdateDataset(WithDatasetPostData, WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):
    
    @test_settings
    def test_update(self):
        
        observation_form = self.create_observation_form()

        dataset = self.create_dataset(observation_form)
        dataset.user = self.user
        dataset.save()

        secondary_user = self.create_secondary_user()

        self.assertEqual(dataset.user, self.user)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)

        post_data = self.get_post_data(alternative_data=True)
        response = self.client.put(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # log in with wrong user
        self.client.force_authenticate(user=secondary_user)

        response = self.client.put(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # log in correct user, client_id is irellevant
        self.client.force_authenticate(user=self.user)

        post_data['clientId'] = 'id differs from dataset'
        response = self.client.put(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        dataset.refresh_from_db()

        self.assertEqual(dataset.data, post_data['data'])


    @test_settings
    def test_update_wrong_app(self):

        observation_form = self.create_observation_form()

        dataset = self.create_dataset(observation_form)
        dataset.user = self.user
        dataset.save()

        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)

        post_data = self.get_post_data(alternative_data=True)

        # log in correct user
        self.client.force_authenticate(user=self.user)

        response = self.client.put(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)



    @test_settings
    def test_update_ao(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)
        dataset.app_uuid = self.ao_app.uuid
        dataset.save()

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)


        post_data = self.get_post_data(alternative_data=True)

        response = self.client.put(url, post_data, format='json')

        # wrong app assigned to dataset, 401 instead of 403 because user is not ligged in
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # assign correct app
        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)

        post_data = self.get_post_data(alternative_data=True)

        response = self.client.put(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        dataset.refresh_from_db()

        self.assertEqual(dataset.data, post_data['data'])


class TestDeleteDataset(WithDatasetPostData, WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):
    
    @test_settings
    def test_destroy(self):
        
        observation_form = self.create_observation_form()

        secondary_user = self.create_secondary_user()

        dataset = self.create_dataset(observation_form)
        dataset.user = self.user
        dataset.save()

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)

        # log in with wrong user
        self.client.force_authenticate(user=secondary_user)

        response = self.client.delete(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user)

        response = self.client.delete(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)



    @test_settings
    def test_destroy_ao(self):
        
        observation_form = self.create_observation_form()

        dataset = self.create_dataset(observation_form)
        dataset.app_uuid = self.ao_app.uuid
        dataset.save()


        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)


        response = self.client.delete(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        post_data = {
            'clientId' : 'different client id'
        }

        response = self.client.delete(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        post_data = {
            'clientId' : dataset.client_id
        }

        response = self.client.delete(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestGetFilteredDatasets(WithMedia, WithObservationForm, WithUser, WithApp, CreatedUsersMixin,
    APITestCase):

    def setUp(self):
        super().setUp()

        observation_form = self.create_observation_form()
        lacerta_agilis = TEST_TAXA['Lacerta agilis']
        rana_aurora = TEST_TAXA['Rana aurora']

        self.dataset_1 = self.create_dataset(observation_form, taxon=lacerta_agilis)
        self.dataset_2 = self.create_dataset(observation_form, taxon=rana_aurora)

    @test_settings
    def test_no_filters(self):
        
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_get_filtered_datasets', kwargs=url_kwargs)

        response = self.client.post(url, data={}, format='json')

        self.assertEqual(response.status_code, 200)
        
        content = json.loads(response.content)
        self.assertEqual(content['results'][1]['uuid'], str(self.dataset_1.uuid))
        self.assertEqual(content['count'], 2)


    @test_settings
    def test_with_filters(self):
        
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        post_data = {
            'filters' : [
                {
                    'column': 'name_uuid',
                    'value': str(self.dataset_1.taxon.name_uuid),
                    'operator': '='
                }
            ]
        }

        url = reverse('api_get_filtered_datasets', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, 200)
        
        content = json.loads(response.content)
        self.assertEqual(content['results'][0]['uuid'], str(self.dataset_1.uuid))
        self.assertEqual(content['count'], 1)

        # test unequal
        post_data = {
            'filters' : [
                {
                    'column': 'name_uuid',
                    'value': str(self.dataset_1.taxon.name_uuid),
                    'operator': '!='
                }
            ]
        }

        url = reverse('api_get_filtered_datasets', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, 200)
        
        content = json.loads(response.content)
        self.assertEqual(content['results'][0]['uuid'], str(self.dataset_2.uuid))
        self.assertEqual(content['count'], 1)

        #test startswith
        post_data = {
            'filters' : [
                {
                    'column': 'taxon_nuid',
                    'value': self.dataset_1.taxon.taxon_nuid[:-3],
                    'operator': 'startswith'
                }
            ]
        }

        url = reverse('api_get_filtered_datasets', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, 200)
        
        content = json.loads(response.content)
        self.assertEqual(content['results'][0]['uuid'], str(self.dataset_1.uuid))
        self.assertEqual(content['count'], 1)

    @test_settings
    def test_order_by(self):
        
        post_data = {
            'orderBy': 'pk' # default is '-pk'
        }

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_get_filtered_datasets', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, 200)
        
        content = json.loads(response.content)
        self.assertEqual(content['results'][0]['uuid'], str(self.dataset_1.uuid))
        self.assertEqual(content['count'], 2)


class TestCreateDatasetImage(WithMedia, WithDatasetPostData, WithObservationForm, WithUser, WithApp, CreatedUsersMixin,
    APITestCase):


    def get_post_data(self, dataset):

        field_uuid = self.get_image_field_uuid(dataset.observation_form)

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                   content_type='image/jpeg')

        post_data = {
            'dataset': dataset.pk,
            'fieldUuid': field_uuid,
            'clientId': dataset.client_id,
            'image': image,
        }

        return post_data

    @test_settings
    def test_post(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset.user = self.user
        dataset.save()
        
        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_create_dataset_image', kwargs=url_kwargs)

        post_data = self.get_post_data(dataset)

        qry = DatasetImages.objects.all()

        self.assertFalse(qry.exists())

        response = self.client.post(url, post_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.user)

        post_data = self.get_post_data(dataset)
        response = self.client.post(url, post_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())

        dataset_image = qry.first()
        self.assertEqual(dataset_image.dataset, dataset)
        self.assertEqual(str(dataset_image.field_uuid), post_data['fieldUuid'])


    @test_settings
    def test_post_ao(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        
        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_create_dataset_image', kwargs=url_kwargs)

        post_data = self.get_post_data(dataset)

        qry = DatasetImages.objects.all()

        self.assertFalse(qry.exists())

        response = self.client.post(url, post_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(qry.exists())

        dataset_image = qry.first()
        self.assertEqual(dataset_image.dataset, dataset)
        self.assertEqual(str(dataset_image.field_uuid), post_data['fieldUuid'])



class TestDestroyDatasetImage(WithMedia, WithDatasetPostData, WithObservationForm, WithUser, WithApp, CreatedUsersMixin,
    APITestCase):

    @test_settings
    def test_post(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset.user = self.user
        dataset.save()
        dataset_image = self.create_dataset_image(dataset)

        qry = DatasetImages.objects.filter(dataset=dataset)

        self.assertTrue(qry.exists())
        
        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'uuid' : str(dataset.uuid),
            'pk': dataset_image.pk,
        }

        url = reverse('api_destroy_dataset_image', kwargs=url_kwargs)

        response = self.client.delete(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(qry.exists())


    @test_settings
    def test_post_ao(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form)
        dataset.app_uuid = self.ao_app.uuid
        dataset.save()

        dataset_image = self.create_dataset_image(dataset)

        qry = DatasetImages.objects.filter(dataset=dataset)
        self.assertTrue(qry.exists())
        
        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
            'pk': dataset_image.pk,
        }

        url = reverse('api_destroy_dataset_image', kwargs=url_kwargs)

        response = self.client.delete(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        post_data = {
            'clientId': 'wrong client id',
        }

        response = self.client.delete(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        post_data = {
            'clientId': dataset.client_id,
        }

        response = self.client.delete(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)



class TestCreateListUserGeometry(WithUserGeometry, WithUser, WithApp, CreatedUsersMixin, APITestCase):

    @test_settings
    def test_post(self):
        
        post_data = {
            'geometry': GEOJSON_POLYGON,
            'name': TEST_USER_GEOMETRY_NAME
        }

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_create_list_user_geometry', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    @test_settings
    def test_post_maxed_out(self):

        self.client.force_authenticate(user=self.user)

        for name in ['poly1', 'poly2', 'poly3']:

            self.create_user_geometry(self.user, name=name)

        
        post_data = {
            'geometry': GEOJSON_POLYGON,
            'name': TEST_USER_GEOMETRY_NAME
        }

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_create_list_user_geometry', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)



    @test_settings
    def test_get(self):
        
        user_geometry = self.create_user_geometry(self.user)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_create_list_user_geometry', kwargs=url_kwargs)

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


        self.client.force_authenticate(user=self.user)
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)
        
        data = response.data['results'][0]
        self.assertEqual(data['id'], user_geometry.id)
        self.assertEqual(data['name'], user_geometry.name)
        self.assertEqual(dict(data['geometry']), GEOJSON_POLYGON)


class TestManageUserGeometry(WithUserGeometry, WithUser, WithApp, CreatedUsersMixin, APITestCase):

    @test_settings
    def test_get(self):
        
        user_geometry = self.create_user_geometry(self.user)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'pk': user_geometry.pk,
        }

        url = reverse('api_manage_user_geometry', kwargs=url_kwargs)

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['geometry'], GEOJSON_POLYGON)
        self.assertEqual(response.data['name'], user_geometry.name)


    @test_settings
    def test_delete(self):
        
        user_geometry = self.create_user_geometry(self.user)

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'pk': user_geometry.pk,
        }

        url = reverse('api_manage_user_geometry', kwargs=url_kwargs)

        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


from anycluster.definitions import GEOMETRY_TYPE_VIEWPORT, GEOMETRY_TYPE_AREA
from anycluster.tests.common import GEOJSON_RECTANGLE

GRID_SIZE = 256
ZOOM = 10

class TestComplexAnyclusterRequests(WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):


    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)


    @test_settings
    def test_get_taxonomic_map_content_count(self):
        
        url_kwargs = {
            'zoom': ZOOM,
            'grid_size': GRID_SIZE,
            'app_uuid': self.app.uuid,
        }

        url = reverse('schema_get_map_content_count', kwargs=url_kwargs)

        filters = []
        modulations = {}

        post_data = {
            'geometry_type': GEOMETRY_TYPE_VIEWPORT,
            'geojson': GEOJSON_RECTANGLE,
            'filters': filters,
            'modulations': modulations
        }

        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        expected_response = {
            'count' : 0,
            'modulations' : {}
        }

        self.assertEqual(parsed_response, expected_response)

        # add one reptile and amphib
        lacerta_agilis = TEST_TAXA['Lacerta agilis']
        rana_aurora = TEST_TAXA['Rana aurora']
        bufo_bufo = TEST_TAXA['Bufo bufo']

        amphibia = TEST_TAXA['Amphibia']
        reptilia = TEST_TAXA['Reptilia']

        dataset_1 = self.create_dataset(self.observation_form, taxon=lacerta_agilis)
        dataset_2 = self.create_dataset(self.observation_form, taxon=rana_aurora)


        modulations = {
            'Amphibia' : {
                'filters' : [
                    {
                        'column': 'taxon_source',
                        'value': amphibia['taxonSource'],
                        'operator': '=',
                    },
                    {
                        'column': 'taxon_nuid',
                        'value': amphibia['taxonNuid'],
                        'operator': 'startswith',
                        'logicalOperator': 'AND'
                    }
                ]
            }
        }

        post_data['modulations'] = modulations

        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        expected_response = {
            'count': 2,
            'modulations': {
                'Amphibia': {
                    'count': 1
                }
            }
        }

        self.assertEqual(parsed_response, expected_response)


        dataset_3 = self.create_dataset(self.observation_form, taxon=bufo_bufo)

        # complex taxonfilter
        modulations = {
            'Amphibia&Reptilia' : {
                'filters' : [
                    {
                        'filters' : [
                            {
                                'column': 'taxon_source',
                                'value': amphibia['taxonSource'],
                                'operator': '=',
                            },
                            {
                                'column': 'taxon_nuid',
                                'value': amphibia['taxonNuid'],
                                'operator': 'startswith',
                                'logicalOperator': 'AND'
                            }
                        ]
                    },
                    {
                        'filters' : [
                            {
                                'column': 'taxon_source',
                                'value': reptilia['taxonSource'],
                                'operator': '=',
                            },
                            {
                                'column': 'taxon_nuid',
                                'value': reptilia['taxonNuid'],
                                'operator': 'startswith',
                                'logicalOperator': 'AND'
                            }
                        ],
                        'logicalOperator' : 'OR',
                    }
                ]
            },
            'Amphibia': {
                'filters': [
                    {
                        'column': 'taxon_source',
                        'value': amphibia['taxonSource'],
                        'operator': '=',
                    },
                    {
                        'column': 'taxon_nuid',
                        'value': amphibia['taxonNuid'],
                        'operator': 'startswith',
                        'logicalOperator': 'AND'
                    }
                ]
            },
            'Reptilia' : {
                'filters' : [
                    {
                        'column': 'taxon_source',
                        'value': reptilia['taxonSource'],
                        'operator': '=',
                    },
                    {
                        'column': 'taxon_nuid',
                        'value': reptilia['taxonNuid'],
                        'operator': 'startswith',
                        'logicalOperator': 'AND'
                    }
                ]
            }
        }

        post_data['modulations'] = modulations

        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        expected_response = {
            'count': 3,
            'modulations': {
                'Amphibia&Reptilia': {
                    'count': 3
                },
                'Amphibia': {
                    'count' : 2,
                },
                'Reptilia': {
                    'count' : 1,
                }
            }
        }

        self.assertEqual(parsed_response, expected_response)

    @test_settings
    def test_get_observation_form_map_content_counts(self):

        lacerta_agilis = TEST_TAXA['Lacerta agilis']
        rana_aurora = TEST_TAXA['Rana aurora']

        dataset_1 = self.create_dataset(self.observation_form, taxon=lacerta_agilis)
        dataset_2 = self.create_dataset(self.observation_form, taxon=rana_aurora)

        url_kwargs = {
            'zoom': ZOOM,
            'grid_size': GRID_SIZE,
            'app_uuid': self.app.uuid,
        }

        url = reverse('schema_get_map_content_count', kwargs=url_kwargs)

        filters = []
        modulations = {
            'Observation form' : {
                'column' : 'observation_form_id',
                'value': self.observation_form.id,
                'operator': '=',
            }
        }

        post_data = {
            'geometry_type': GEOMETRY_TYPE_VIEWPORT,
            'geojson': GEOJSON_RECTANGLE,
            'filters': filters,
            'modulations': modulations
        }

        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        expected_response = {
            'count': 2,
            'modulations': {
                'Observation form': {
                    'count': 2
                }
            }
        }
        
        self.assertEqual(parsed_response, expected_response)


    @test_settings
    def test_get_grouped_map_contents(self):


        url_kwargs = {
            'zoom': ZOOM,
            'grid_size': GRID_SIZE,
            'app_uuid': self.app.uuid,
        }

        filters = []

        post_data = {
            'geometry_type': GEOMETRY_TYPE_VIEWPORT,
            'geojson': GEOJSON_RECTANGLE,
            'filters': filters,
            'group_by': 'name_uuid',
        }

        url = reverse('schema_get_grouped_map_contents', kwargs=url_kwargs)

        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        self.assertEqual(parsed_response, {})

        lacerta_agilis = TEST_TAXA['Lacerta agilis']
        rana_aurora = TEST_TAXA['Rana aurora']
        bufo_bufo = TEST_TAXA['Bufo bufo']


        dataset_1 = self.create_dataset(self.observation_form, taxon=lacerta_agilis)
        dataset_2 = self.create_dataset(self.observation_form, taxon=rana_aurora)
        dataset_3 = self.create_dataset(self.observation_form, taxon=rana_aurora)
        dataset_4 = self.create_dataset(self.observation_form, taxon=rana_aurora)
        dataset_5 = self.create_dataset(self.observation_form, taxon=lacerta_agilis)


        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        expected_response = {
            'b9d5f692-e296-4890-9d13-ee68273edda0': {
                'count': 3,
                'taxon': {
                    'nameUuid': 'b9d5f692-e296-4890-9d13-ee68273edda0',
                    'taxonSource': 'taxonomy.sources.col',
                    'taxonLatname': 'Rana aurora',
                    'taxonAuthor': 'Baird and Girard, 1852',
                    'taxonNuid': '00100800200101600e004'
                }
            },
            'c36819f7-4b65-477b-8756-389289c531ec': {
                'count': 2,
                'taxon': {
                    'nameUuid': 'c36819f7-4b65-477b-8756-389289c531ec',
                    'taxonSource': 'taxonomy.sources.col',
                    'taxonLatname': 'Lacerta agilis',
                    'taxonAuthor': 'Linnaeus, 1758',
                    'taxonNuid': '00100800c00301000m001'
                }
            }
        }

        self.assertEqual(parsed_response, expected_response)


'''
    Test the image url when getting datasets
'''
class TestGetAreaContent(WithMedia, WithObservationForm, WithUser, WithApp, CreatedUsersMixin, APITestCase):


    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)


    def test_get_area_content(self):

        dataset = self.create_dataset(observation_form=self.observation_form)
        dataset.user = self.user
        dataset.save()
        dataset_image = self.create_dataset_image(dataset)

        qry = DatasetImages.objects.filter(dataset=dataset)

        self.assertTrue(qry.exists())

        self.assertTrue(dataset.thumbnail.endswith('.jpg'))


        url_kwargs = {
            'zoom': ZOOM,
            'grid_size': GRID_SIZE,
            'app_uuid': self.app.uuid,
        }

        url = reverse('schema_get_area_content', kwargs=url_kwargs)

        post_data = {
            'geometry_type': GEOMETRY_TYPE_AREA,
            'geojson': GEOJSON_RECTANGLE,
            'filters': [],
        }

        response = self.client.post(url, post_data, format='json')

        parsed_response = json.loads(response.content)

        retrieved_dataset = parsed_response[0]

        self.assertEqual(retrieved_dataset['uuid'], str(dataset.uuid))

        self.assertIn('images', retrieved_dataset)

        field_uuid = None
        for field in self.observation_form.definition['fields']:
            
            if field['fieldClass'] == 'PictureField':
                field_uuid = field['uuid']
                break

        image = retrieved_dataset['images'][field_uuid][0]
        self.assertIn('imageUrl', image)
        