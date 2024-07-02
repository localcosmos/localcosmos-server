from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings

from localcosmos_server.datasets.views import (ListDatasets, HumanInteractionValidationView, EditDataset,
            AjaxSaveDataset, AjaxLoadFormFieldImages, LargeModalImage, ShowDatasetValidationRoutine,
            ManageDatasetValidationRoutineStep, DeleteDatasetValidationRoutineStep, DeleteDataset,
            DeleteDatasetImage, DownloadDatasetsCSV)


from localcosmos_server.tests.mixins import (WithObservationForm, WithApp, WithUser, WithValidationRoutine, WithMedia,
                                             CommonSetUp)

from localcosmos_server.tests.common import test_settings, DataCreator

from localcosmos_server.datasets.models import DatasetValidationRoutine

import os, json

class TestListDatasets(CommonSetUp, WithObservationForm, WithUser, WithApp, TestCase):

    @test_settings
    def test_get_context_data(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)
        
        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        request = self.factory.get(reverse('datasets:list_datasets', kwargs=url_kwargs))
        request.session = self.client.session
        request.app = self.app

        view = ListDatasets()        
        view.request = request

        context = view.get_context_data()

        self.assertEqual(len(context['datasets']), 1)


class TestHumanInteractionValidationView(CommonSetUp, WithValidationRoutine, WithObservationForm, WithUser,
                                         WithApp, TestCase):
    
    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form()
        self.dataset = self.create_dataset(self.observation_form)

    def get_url_kwargs(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
            'validation_step_id' : self.validation_step.id,
        }

        return url_kwargs
    
    def get_view(self):

        self.create_validation_routine()

        self.validation_step = DatasetValidationRoutine.objects.get(app=self.app,
                validation_class='localcosmos_server.datasets.validation.ExpertReviewValidator')

        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse('datasets:human_validation', kwargs=url_kwargs))
        request.session = self.client.session
        request.app = self.app
        request.user = self.user

        view = HumanInteractionValidationView()
        view.request = request

        return view, request
    
    @test_settings
    def test_dispatch(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(view.dataset, self.dataset)
        self.assertEqual(view.validation_step, self.validation_step)


    @test_settings
    def test_get_observation_form(self):

        view, request = self.get_view()
        view.dataset = self.dataset
        observation_form = view.get_observation_form()
        self.assertTrue(isinstance(observation_form, view.observation_form_class))


    @test_settings
    def test_get_context_data(self):

        view, request = self.get_view()
        view.dataset = self.dataset
        view.validation_step = self.validation_step

        ValidatorClass = self.validation_step.get_class()
        validator = ValidatorClass(self.validation_step)
        view.form_class = validator.form_class
        
        context_data = view.get_context_data(**{})

        self.assertEqual(context_data['dataset'], self.dataset)
        self.assertEqual(context_data['validation_step'], self.validation_step)
        self.assertEqual(context_data['observation_form'].__class__, view.observation_form_class)


    @test_settings
    def test_form_valid(self):

        view, request = self.get_view()
        view.dataset = self.dataset
        view.validation_step = self.validation_step

        url_kwargs = self.get_url_kwargs()

        view.kwargs = url_kwargs

        ValidatorClass = self.validation_step.get_class()
        validator = ValidatorClass(self.validation_step)
        view.form_class = validator.form_class
        view.validator = validator

        view.template_name = validator.template_name

        post_data = {
            'dataset_is_valid' : 'is_valid',
        }

        form = view.form_class(post_data)
        self.assertTrue(form.is_valid())
        
        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_get(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()
        response = self.client.get(reverse('datasets:human_validation', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_post(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        post_data = {
            'dataset_is_valid' : 'is_valid',
        }
        
        response = self.client.post(reverse('datasets:human_validation', kwargs=url_kwargs), post_data)

        self.assertEqual(response.status_code, 200)



class TestEditDataset(CommonSetUp, WithObservationForm, WithUser, WithApp, TestCase):

    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form()
        self.dataset = self.create_dataset(self.observation_form)

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
        }

        return url_kwargs
        

    def get_view(self):

        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse('datasets:edit_dataset', kwargs=url_kwargs))
        request.session = self.client.session
        request.app = self.app
        request.user = self.user

        view = EditDataset()
        view.request = request

        return view, request
    
    @test_settings
    def test_dispatch(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(view.dataset, self.dataset)
        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_get_form(self):

        view, request = self.get_view()

        view.dataset = self.dataset

        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)
        

    @test_settings
    def test_get_context_data(self):

        view, request = self.get_view()

        view.dataset = self.dataset

        context_data = view.get_context_data()

        self.assertEqual(context_data['dataset'], self.dataset)
        
    @test_settings
    def test_get(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()
        response = self.client.get(reverse('datasets:edit_dataset', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 200)


class TestAjaxSaveDataset(CommonSetUp, WithObservationForm, WithUser, WithApp, TestCase):

    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form()
        self.dataset = self.create_dataset(self.observation_form)


    def get_post_data(self):

        post_data = {}

        taxonomic_reference_uuid = self.observation_form.definition['taxonomicReference']
        geographic_reference_uuid = self.observation_form.definition['geographicReference']
        temporal_reference_uuid = self.observation_form.definition['temporalReference']

        post_data['{0}_0'.format(taxonomic_reference_uuid)] = 'taxonomy.sources.col'
        post_data['{0}_1'.format(taxonomic_reference_uuid)] = 'Picea abies changed'
        post_data['{0}_2'.format(taxonomic_reference_uuid)] = 'Linnaeus changed'
        post_data['{0}_3'.format(taxonomic_reference_uuid)] = '1541aa08-7c23-4de0-9898-80d87e9227b4'
        post_data['{0}_4'.format(taxonomic_reference_uuid)] = '006002009001005007002'

        post_data['{0}_0'.format(geographic_reference_uuid)] = 'Verbose area name'
        post_data['{0}_1'.format(geographic_reference_uuid)] = json.dumps({
            "type": "Feature",
            "geometry": {
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "EPSG:4326"
                    }
                },
                "type": "Point",
                "coordinates": [33.33, 44.44]
            },
            "properties": {
                "accuracy": 1
            }
        })

        post_data[temporal_reference_uuid] = "2014-01-02T11:42Z"

        # regular fields
        post_data['ac4b0a7a-8fd0-439f-8874-0f146409d478'] = 'CharField content'
        post_data['a3217a33-4c76-4d34-befd-d2f5195d1d66'] = 2.5
        post_data['d451ca95-2324-413e-861d-71dd8aaa6e15'] = ['wahl 1', 'wahl 2']
        post_data['35ed00ea-c364-455c-8765-c13ab9665307_0'] = 'Verbose point name'
        post_data['35ed00ea-c364-455c-8765-c13ab9665307_1'] = post_data['{0}_1'.format(geographic_reference_uuid)]
        post_data['95663afc-2f14-4087-9722-248cee51ba11'] = 'true' # BooleanField
        post_data['1b35044c-2f26-4d92-85ff-b56a667a1741'] = '4'
        post_data['a4af5d5f-17c8-45b7-9a31-9065aa9b183c'] = 1.234 # float
        post_data['2187e7d8-be9f-449b-b07d-aac768e8a64a'] = 'wahl 1' # choice

        return post_data

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
        }
        
        return url_kwargs

    def get_view(self):

        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse('datasets:save_dataset', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        request.method = 'POST'
        request.POST = self.get_post_data()

        view = AjaxSaveDataset()
        view.request = request
        view.kwargs = url_kwargs

        return view, request
        
    @test_settings
    def test_dispatch(self):

        view, request = self.get_view()
        url_kwargs = self.get_url_kwargs()
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.dataset, self.dataset)

    @test_settings
    def test_get_context_data(self):

        view, request = self.get_view()
        view.dataset = self.dataset

        context_data = view.get_context_data(**{})

        self.assertEqual(context_data['dataset'], self.dataset)
        self.assertEqual(context_data['form'].__class__, view.form_class)

    @test_settings
    def test_get_form(self):

        view, request = self.get_view()
        view.dataset = self.dataset

        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)


    @test_settings
    def test_form_valid(self):

        view, request = self.get_view()
        view.dataset = self.dataset

        old_data = view.dataset.data.copy()

        post_data = self.get_post_data()
        form = view.form_class(view.request.app, view.dataset, data=post_data)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.context_data['success'], True)

        self.dataset.refresh_from_db()

        taxonomic_reference_uuid = self.observation_form.definition['taxonomicReference']
        geographic_reference_uuid = self.observation_form.definition['geographicReference']
        temporal_reference_uuid = self.observation_form.definition['temporalReference']

        # check all submitted values
        for key, value in post_data.items():

            if '_' in key:

                field_uuid = key.split('_')[0]
                
                dataset_value = self.dataset.data[field_uuid]

                if field_uuid == taxonomic_reference_uuid:

                    if key == '{0}_0'.format(taxonomic_reference_uuid):
                        # taxon
                        self.assertEqual(dataset_value['taxonSource'], value)

                    elif key == '{0}_1'.format(taxonomic_reference_uuid):
                        # taxon
                        self.assertEqual(dataset_value['taxonLatname'], value)
                        
                    elif key == '{0}_2'.format(taxonomic_reference_uuid):
                        # taxon
                        self.assertEqual(dataset_value['taxonAuthor'], value)

                    elif key == '{0}_3'.format(taxonomic_reference_uuid):
                        # taxon
                        self.assertEqual(dataset_value['nameUuid'], value)

                    elif key == '{0}_4'.format(taxonomic_reference_uuid):
                        # taxon
                        self.assertEqual(dataset_value['taxonNuid'], value)

                elif field_uuid == geographic_reference_uuid:

                    if key == '{0}_1'.format(geographic_reference_uuid):
                        geojson = json.loads(value)
                        self.assertEqual(dataset_value, geojson)

                elif key == '35ed00ea-c364-455c-8765-c13ab9665307_1':
                    self.assertEqual(dataset_value, json.loads(value))

            else:

                dataset_value = self.dataset.data[key]
                

                if key == temporal_reference_uuid:
                    # time, ignored
                    self.assertEqual(dataset_value, old_data[key])

                elif key == '95663afc-2f14-4087-9722-248cee51ba11':
                    # bool
                    self.assertTrue(dataset_value)

                elif key == 'ac4b0a7a-8fd0-439f-8874-0f146409d478':
                    # charfield
                    self.assertEqual(dataset_value, value)

                elif key == '2187e7d8-be9f-449b-b07d-aac768e8a64a':
                    # choice
                    self.assertEqual(dataset_value, value)

                elif key == 'a3217a33-4c76-4d34-befd-d2f5195d1d66':
                    # decimal
                    self.assertEqual(dataset_value, float(value))

                elif key == 'a4af5d5f-17c8-45b7-9a31-9065aa9b183c':
                    # float
                    self.assertEqual(dataset_value, float(value))
                
                elif key == '1b35044c-2f26-4d92-85ff-b56a667a1741':
                    # int
                    self.assertEqual(dataset_value, int(value))

                elif key == 'd451ca95-2324-413e-861d-71dd8aaa6e15':
                    # multiple choice
                    self.assertEqual(dataset_value, value)
                

    @test_settings
    def test_post(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        post_data = self.get_post_data()
        response = self.client.post(reverse('datasets:save_dataset', kwargs=url_kwargs), post_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_loggedout(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        self.client.logout()

        post_data = self.get_post_data()
        response = self.client.post(reverse('datasets:save_dataset', kwargs=url_kwargs), post_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 302)


    @test_settings
    def test_bad_request_no_ajax(self):

        view, request = self.get_view()
        url_kwargs = self.get_url_kwargs()

        post_data = self.get_post_data()
        response = self.client.post(reverse('datasets:save_dataset', kwargs=url_kwargs), post_data)

        self.assertEqual(response.status_code, 400)
        


class TestAjaxLoadFormFieldImages(CommonSetUp, WithObservationForm, WithUser, WithApp, WithMedia, TestCase):

    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form()
        self.dataset = self.create_dataset(self.observation_form)

        self.picture_field_uuid = self.get_image_field_uuid(self.observation_form)

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
        }
        
        return url_kwargs

    def get_view(self):

        self.dataset_image = self.create_dataset_image(self.dataset)

        url_kwargs = self.get_url_kwargs()

        get_data = {
            'field_uuid' : self.picture_field_uuid,
        }
        
        request = self.factory.get(reverse('datasets:load_form_field_images', kwargs=url_kwargs), get_data)
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        view = AjaxLoadFormFieldImages()
        view.request = request
        view.kwargs = url_kwargs

        return view, request
        
    @test_settings
    def test_dispatch(self):

        view, request = self.get_view()
        url_kwargs = self.get_url_kwargs()
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.dataset, self.dataset)
        self.assertEqual(view.field_uuid, self.picture_field_uuid)
        
    @test_settings
    def test_get_context_data(self):
        view, request = self.get_view()
        view.dataset = self.dataset
        view.field_uuid = self.picture_field_uuid
        
        context = view.get_context_data(**{})
        self.assertEqual(context['images'].first(), self.dataset_image)


    @test_settings
    def test_get(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        get_data = {
            'field_uuid' : self.picture_field_uuid,
        }
        
        response = self.client.get(reverse('datasets:load_form_field_images', kwargs=url_kwargs), get_data,
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_loggedout(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        get_data = {
            'field_uuid' : self.picture_field_uuid,
        }

        self.client.logout()
        
        response = self.client.get(reverse('datasets:load_form_field_images', kwargs=url_kwargs), get_data,
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 302)


    @test_settings
    def test_bad_request_no_ajax(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        get_data = {
            'field_uuid' : self.picture_field_uuid,
        } 
        
        response = self.client.get(reverse('datasets:load_form_field_images', kwargs=url_kwargs), get_data)

        self.assertEqual(response.status_code, 400)
        
        
class TestLargeModalImage(WithApp, TestCase):

    url_name = 'datasets:large_modal_image'

    @test_settings
    def test_get_context_data(self):

        self.factory = RequestFactory()

        get_data = {
            'image_url' : 'test/test_image_url.jpg',
        }

        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        
        request = self.factory.get(reverse(self.url_name, kwargs=url_kwargs), get_data)
        

        view = LargeModalImage()
        view.request = request
        view.kwargs = url_kwargs

        context = view.get_context_data(**{})
        self.assertEqual(context['image_url'], get_data['image_url'])

        

class TestShowDatasetValidationRoutine(CommonSetUp, WithObservationForm, WithUser, WithApp, WithMedia,
                                       WithValidationRoutine, TestCase):

    url_name = 'datasets:dataset_validation_routine'

    @test_settings
    def test_get_context_data(self):

        self.create_validation_routine()

        self.factory = RequestFactory()

        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        
        request = self.factory.get(reverse(self.url_name, kwargs=url_kwargs), {})
        request.app = self.app
        
        view = ShowDatasetValidationRoutine()
        view.request = request
        view.kwargs = url_kwargs

        context = view.get_context_data(**{})

        expected_classes = list(settings.DATASET_VALIDATION_CLASSES)
        self.assertEqual(len(context['available_validation_classes']), 1)



class TestManageDatasetValidationRoutineStep(CommonSetUp, WithObservationForm, WithUser, WithApp,
                                             WithValidationRoutine, TestCase):
    
    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form()
        self.dataset = self.create_dataset(self.observation_form)


    post_data = {
        'validation_step' : 'localcosmos_server.datasets.validation.ExpertReviewValidator',
        'position' : 1,
    }


    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        return url_kwargs


    def get_manage_url_kwargs(self):

        validation_step = self.get_validation_step()
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk' : validation_step.pk,
        }

        return url_kwargs
    

    def get_validation_step(self):
        validation_step = DatasetValidationRoutine.objects.get(app=self.app,
                    validation_class='localcosmos_server.datasets.validation.ExpertReviewValidator')

        return validation_step


    def get_validation_routine(self):
        return DatasetValidationRoutine.objects.filter(app=self.app)
    

    def get_view(self, url_name, url_kwargs, get_data={}):
        
        request = self.factory.get(reverse(url_name, kwargs=url_kwargs), get_data)
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        view = ManageDatasetValidationRoutineStep()
        view.request = request
        view.kwargs = url_kwargs

        return view, request
        

    @test_settings
    def test_dispatch_add(self):

        url_kwargs = self.get_url_kwargs()        

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_dispatch_manage(self):

        self.create_validation_routine()

        validation_step = self.get_validation_step()


        url_kwargs = self.get_manage_url_kwargs()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.validation_step, validation_step)


    @test_settings
    def test_get_form_kwargs_add(self):

        url_kwargs = self.get_url_kwargs()        

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)
        view.validation_step = None
        
        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['instance'], None)
        

    @test_settings
    def test_get_form_kwargs_manage(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        validation_step = self.get_validation_step()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        view.validation_step = validation_step
        
        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['instance'], validation_step)
        

    @test_settings
    def test_get_form(self):

        url_kwargs = self.get_url_kwargs()

        validation_routine = self.get_validation_routine()

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)
        view.validation_routine = validation_routine
        view.validation_step = None
        
        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)
        self.assertEqual(form.validation_routine, validation_routine)


    @test_settings
    def test_get_context_data(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        validation_step = self.get_validation_step()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        view.validation_routine = self.get_validation_routine()
        view.validation_step = validation_step
        
        context = view.get_context_data()

        self.assertEqual(context['validation_step'], validation_step)
        

    @test_settings
    def test_get_initial(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        validation_step = self.get_validation_step()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        view.validation_routine = self.get_validation_routine()
        view.validation_step = validation_step
        
        initial = view.get_initial()

        self.assertEqual(initial['validation_step'], validation_step.validation_class)
        self.assertEqual(initial['position'], validation_step.position)


    @test_settings
    def test_get_manage(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        response = self.client.get(reverse('datasets:manage_dataset_validation_routine_step', kwargs=url_kwargs),
                                   {}, HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_get_add(self):

        self.create_validation_routine()

        url_kwargs = self.get_url_kwargs()

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)

        response = self.client.get(reverse('datasets:add_dataset_validation_routine_step', kwargs=url_kwargs),
                                   {}, HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        

    @test_settings
    def test_form_valid_add(self):

        url_kwargs = self.get_url_kwargs()

        validation_step = None

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)

        view.validation_routine = self.get_validation_routine()
        view.validation_step = validation_step
        
        form = view.form_class(view.validation_routine, data=self.post_data)

        form.is_valid()

        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'] , True)

        validation_step = self.get_validation_step()
        self.assertEqual(response.context_data['validation_step'], validation_step)
        self.assertEqual(response.context_data['form'].__class__, view.form_class)


    @test_settings
    def test_form_valid_manage(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        validation_step = self.get_validation_step()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        view.validation_routine = self.get_validation_routine()
        view.validation_step = validation_step
        
        form = view.form_class(view.validation_routine, instance=validation_step, data=self.post_data)

        form.is_valid()

        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'] , True)

        validation_step = self.get_validation_step()
        self.assertEqual(response.context_data['validation_step'], validation_step)
        self.assertEqual(response.context_data['form'].__class__, view.form_class)
        

    @test_settings
    def test_get_no_ajax_bad_request(self):

        self.create_validation_routine()

        url_kwargs = self.get_url_kwargs()

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)

        response = self.client.get(reverse('datasets:add_dataset_validation_routine_step', kwargs=url_kwargs),
                                   {})

        self.assertEqual(response.status_code, 400)


    @test_settings
    def test_post(self):

        url_kwargs = self.get_url_kwargs()

        validation_step = None

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)


        response = self.client.post(reverse('datasets:add_dataset_validation_routine_step', kwargs=url_kwargs),
                                   self.post_data, HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        


class TestDownloadDatasetsCSV(CommonSetUp, WithObservationForm, WithUser, WithApp, WithMedia, TestCase):

    def setUp(self):
        super().setUp()

        self.observation_form = self.create_observation_form()
        self.dataset = self.create_dataset(self.observation_form)

    @test_settings
    def test_get(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        url = reverse('datasets:download_datasets_csv', kwargs=url_kwargs)
        response = self.client.get(url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        #self.assertTrue(os.path.isfile(response['X-Sendfile']))
        
