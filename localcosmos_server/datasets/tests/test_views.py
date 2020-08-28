from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings

from localcosmos_server.datasets.views import (ListDatasets, HumanInteractionValidationView, EditDataset,
            AjaxSaveDataset, AjaxLoadFormFieldImages, LargeModalImage, ShowDatasetValidationRoutine,
            ManageDatasetValidationRoutineStep, DeleteDatasetValidationRoutineStep, DeleteDataset,
            DeleteDatasetImage, DownloadDatasetsCSV)


from localcosmos_server.tests.mixins import (WithDataset, WithApp, WithUser, WithValidationRoutine, WithMedia,
                                             CommonSetUp)

from localcosmos_server.tests.common import test_settings

from localcosmos_server.datasets.models import DatasetValidationRoutine

import os



@test_settings
class TestListDatasets(CommonSetUp, WithDataset, WithUser, WithApp, TestCase):

    def test_get_context_data(self):

        self.create_dataset()
        
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


@test_settings
class TestHumanInteractionValidationView(CommonSetUp, WithValidationRoutine, WithDataset, WithUser, WithApp,
                                         TestCase):

    def get_url_kwargs(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
            'validation_step_id' : self.validation_step.id,
        }

        return url_kwargs
    
    def get_view(self):

        self.dataset = self.create_dataset()

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
        
    def test_dispatch(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(view.dataset, self.dataset)
        self.assertEqual(view.validation_step, self.validation_step)


    def test_get_observation_form(self):

        view, request = self.get_view()
        view.dataset = self.dataset
        observation_form = view.get_observation_form()
        self.assertTrue(isinstance(observation_form, view.observation_form_class))


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

    def test_get(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()
        response = self.client.get(reverse('datasets:human_validation', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 200)

    def test_post(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        post_data = {
            'dataset_is_valid' : 'is_valid',
        }
        
        response = self.client.post(reverse('datasets:human_validation', kwargs=url_kwargs), post_data)

        self.assertEqual(response.status_code, 200)


@test_settings
class TestEditDataset(CommonSetUp, WithDataset, WithUser, WithApp, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
        }

        return url_kwargs
        

    def get_view(self):

        self.dataset = self.create_dataset()

        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse('datasets:edit_dataset', kwargs=url_kwargs))
        request.session = self.client.session
        request.app = self.app
        request.user = self.user

        view = EditDataset()
        view.request = request

        return view, request
        
    def test_dispatch(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(view.dataset, self.dataset)
        self.assertEqual(response.status_code, 200)


    def test_get_form(self):

        view, request = self.get_view()

        view.dataset = self.dataset

        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)
        

    def test_get_context_data(self):

        view, request = self.get_view()

        view.dataset = self.dataset

        context_data = view.get_context_data()

        self.assertEqual(context_data['dataset'], self.dataset)
        

    def test_get(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()
        response = self.client.get(reverse('datasets:edit_dataset', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 200)


@test_settings
class TestAjaxSaveDataset(CommonSetUp, WithDataset, WithUser, WithApp, TestCase):


    post_data = {
        "7dfd9ff4-456e-426d-9772-df5824dab18f_0" : "taxonomy.sources.col", # source
        "7dfd9ff4-456e-426d-9772-df5824dab18f_1" : "Picea abies changed", # latname
        "7dfd9ff4-456e-426d-9772-df5824dab18f_2" : "Linnaeus changed", # latname
        "7dfd9ff4-456e-426d-9772-df5824dab18f_3" : "1541aa08-7c23-4de0-9898-80d87e9227b4", # uuid
        "7dfd9ff4-456e-426d-9772-df5824dab18f_4" : "006002009001005007002", # nuid
        "98332a11-d56e-4a92-aeda-13e2f74453cb" : {"type": "Feature", "geometry": {"crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "type": "Point", "coordinates": [33.33, 44.44]}, "properties": {"accuracy": 1}},
        "33cf1019-c8a1-4091-8c23-c95489c39094" : {"cron": {"type": "timestamp", "format": "unixtime", "timestamp": 1234567, "timezone_offset": 120}, "type": "Temporal"},
        "e46c1a77-2070-49b4-a027-ca6b345cdca3" : "on", # BooleanField
        "25efa219-c631-4701-98ed-d007f1acf3de" : "text", # CharField
        "3f96ddc1-1d1b-4a52-a24c-b94d3e063923" : "choice 2",
        "4b62fae2-0e6f-49e5-87a5-6a0756449273" : "2.2",
        "b4b153d3-7b9b-4a32-b5b1-6ec3e95b6ec7" : "1.5",
        "969d04d9-cbc2-45d1-83cd-1d3450fe8a35" : 3,
        "1125a45a-6d38-4874-910d-b2dedcc7dedb" : ["mc1","mc2"],
    }

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
        }
        
        return url_kwargs

    def get_view(self):

        self.dataset = self.create_full_dataset()

        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse('datasets:save_dataset', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        request.method = 'POST'
        request.POST = self.post_data

        view = AjaxSaveDataset()
        view.request = request
        view.kwargs = url_kwargs

        return view, request
        

    def test_dispatch(self):

        view, request = self.get_view()
        url_kwargs = self.get_url_kwargs()
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.dataset, self.dataset)

    def test_get_context_data(self):

        view, request = self.get_view()
        view.dataset = self.dataset

        context_data = view.get_context_data(**{})

        self.assertEqual(context_data['dataset'], self.dataset)
        self.assertEqual(context_data['form'].__class__, view.form_class)

    def test_get_form(self):

        view, request = self.get_view()
        view.dataset = self.dataset

        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)


    def test_form_valid(self):

        view, request = self.get_view()
        view.dataset = self.dataset

        old_data = view.dataset.data.copy()

        form = view.form_class(view.request.app, view.dataset.data, data=self.post_data)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.context_data['success'], True)

        self.dataset.refresh_from_db()

        # check all submitted values
        for key, value in self.post_data.items():

            if '_' in key:

                taxon_key = key.split('_')[0]
                
                dataset_value = self.dataset.data['dataset']['reported_values'][taxon_key]

                if key == "7dfd9ff4-456e-426d-9772-df5824dab18f_0":
                    # taxon
                    self.assertEqual(dataset_value['taxon_source'], value)

                elif key == "7dfd9ff4-456e-426d-9772-df5824dab18f_1":
                    # taxon
                    self.assertEqual(dataset_value['taxon_latname'], value)
                    
                elif key == "7dfd9ff4-456e-426d-9772-df5824dab18f_2":
                    # taxon
                    self.assertEqual(dataset_value['taxon_author'], value)

                elif key == "7dfd9ff4-456e-426d-9772-df5824dab18f_3":
                    # taxon
                    self.assertEqual(dataset_value['name_uuid'], value)

                elif key == "7dfd9ff4-456e-426d-9772-df5824dab18f_4":
                    # taxon
                    self.assertEqual(dataset_value['taxon_nuid'], value)

            else:

                dataset_value = self.dataset.data['dataset']['reported_values'][key]
                
                if key == "98332a11-d56e-4a92-aeda-13e2f74453cb":
                    # location, ignored
                    self.assertEqual(dataset_value, old_data['dataset']['reported_values'][key])

                elif key == "33cf1019-c8a1-4091-8c23-c95489c39094":
                    # time, ignored
                    self.assertEqual(dataset_value, old_data['dataset']['reported_values'][key])

                elif key == "e46c1a77-2070-49b4-a027-ca6b345cdca3":
                    # bool
                    self.assertTrue(dataset_value)

                elif key == "25efa219-c631-4701-98ed-d007f1acf3de":
                    # charfield
                    self.assertEqual(dataset_value, value)

                elif key == "3f96ddc1-1d1b-4a52-a24c-b94d3e063923":
                    # choice
                    self.assertEqual(dataset_value, value)

                elif key == "4b62fae2-0e6f-49e5-87a5-6a0756449273":
                    # decimal
                    self.assertEqual(dataset_value, float(value))

                elif key == "b4b153d3-7b9b-4a32-b5b1-6ec3e95b6ec7":
                    # float
                    self.assertEqual(dataset_value, float(value))
                
                elif key == "969d04d9-cbc2-45d1-83cd-1d3450fe8a35":
                    # int
                    self.assertEqual(dataset_value, int(value))

                elif key == "1125a45a-6d38-4874-910d-b2dedcc7dedb":
                    # multiple choice
                    self.assertEqual(dataset_value, value)


    def test_post(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        response = self.client.post(reverse('datasets:save_dataset', kwargs=url_kwargs), self.post_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


    def test_loggedout(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        self.client.logout()

        response = self.client.post(reverse('datasets:save_dataset', kwargs=url_kwargs), self.post_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 302)


    def test_bad_request_no_ajax(self):

        view, request = self.get_view()
        url_kwargs = self.get_url_kwargs()

        response = self.client.post(reverse('datasets:save_dataset', kwargs=url_kwargs), self.post_data)

        self.assertEqual(response.status_code, 400)
        

@test_settings
class TestAjaxLoadFormFieldImages(CommonSetUp, WithDataset, WithUser, WithApp, WithMedia, TestCase):

    picture_field_uuid = "74763c0c-ea70-4280-940f-5ddb41d74747"

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'dataset_id' : self.dataset.id,
        }
        
        return url_kwargs

    def get_view(self):

        self.dataset = self.create_full_dataset()
        self.dataset_image = self.create_dataset_image(self.dataset, self.picture_field_uuid)

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
        

    def test_dispatch(self):

        view, request = self.get_view()
        url_kwargs = self.get_url_kwargs()
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.dataset, self.dataset)
        self.assertEqual(view.field_uuid, self.picture_field_uuid)
        

    def test_get_context_data(self):
        view, request = self.get_view()
        view.dataset = self.dataset
        view.field_uuid = self.picture_field_uuid
        
        context = view.get_context_data(**{})
        self.assertEqual(context['images'].first(), self.dataset_image)


    def test_get(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        get_data = {
            'field_uuid' : self.picture_field_uuid,
        }
        
        response = self.client.get(reverse('datasets:load_form_field_images', kwargs=url_kwargs), get_data,
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


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


    def test_bad_request_no_ajax(self):

        view, request = self.get_view()

        url_kwargs = self.get_url_kwargs()

        get_data = {
            'field_uuid' : self.picture_field_uuid,
        } 
        
        response = self.client.get(reverse('datasets:load_form_field_images', kwargs=url_kwargs), get_data)

        self.assertEqual(response.status_code, 400)
        
        
@test_settings
class TestLargeModalImage(WithApp, TestCase):

    url_name = 'datasets:large_modal_image'

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

        
@test_settings
class TestShowDatasetValidationRoutine(CommonSetUp, WithDataset, WithUser, WithApp, WithMedia,
                                       WithValidationRoutine, TestCase):

    url_name = 'datasets:dataset_validation_routine'

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


@test_settings
class TestManageDatasetValidationRoutineStep(CommonSetUp, WithDataset, WithUser, WithApp, WithValidationRoutine,
                                             TestCase):


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

        self.dataset = self.create_full_dataset()
        
        request = self.factory.get(reverse(url_name, kwargs=url_kwargs), get_data)
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        view = ManageDatasetValidationRoutineStep()
        view.request = request
        view.kwargs = url_kwargs

        return view, request
        

    def test_dispatch_add(self):

        url_kwargs = self.get_url_kwargs()        

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)


    def test_dispatch_manage(self):

        self.create_validation_routine()

        validation_step = self.get_validation_step()


        url_kwargs = self.get_manage_url_kwargs()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.validation_step, validation_step)


    def test_get_form_kwargs_add(self):

        url_kwargs = self.get_url_kwargs()        

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)
        view.validation_step = None
        
        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['instance'], None)
        

    def test_get_form_kwargs_manage(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        validation_step = self.get_validation_step()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        view.validation_step = validation_step
        
        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['instance'], validation_step)
        

    def test_get_form(self):

        url_kwargs = self.get_url_kwargs()

        validation_routine = self.get_validation_routine()

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)
        view.validation_routine = validation_routine
        view.validation_step = None
        
        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)
        self.assertEqual(form.validation_routine, validation_routine)


    def test_get_context_data(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        validation_step = self.get_validation_step()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        view.validation_routine = self.get_validation_routine()
        view.validation_step = validation_step
        
        context = view.get_context_data()

        self.assertEqual(context['validation_step'], validation_step)
        

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


    def test_get_manage(self):

        self.create_validation_routine()

        url_kwargs = self.get_manage_url_kwargs()

        view, request = self.get_view('datasets:manage_dataset_validation_routine_step', url_kwargs)

        response = self.client.get(reverse('datasets:manage_dataset_validation_routine_step', kwargs=url_kwargs),
                                   {}, HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


    def test_get_add(self):

        self.create_validation_routine()

        url_kwargs = self.get_url_kwargs()

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)

        response = self.client.get(reverse('datasets:add_dataset_validation_routine_step', kwargs=url_kwargs),
                                   {}, HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        

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
        

    def test_get_no_ajax_bad_request(self):

        self.create_validation_routine()

        url_kwargs = self.get_url_kwargs()

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)

        response = self.client.get(reverse('datasets:add_dataset_validation_routine_step', kwargs=url_kwargs),
                                   {})

        self.assertEqual(response.status_code, 400)


    def test_post(self):

        url_kwargs = self.get_url_kwargs()

        validation_step = None

        view, request = self.get_view('datasets:add_dataset_validation_routine_step', url_kwargs)


        response = self.client.post(reverse('datasets:add_dataset_validation_routine_step', kwargs=url_kwargs),
                                   self.post_data, HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        


@test_settings
class TestDownloadDatasetsCSV(CommonSetUp, WithDataset, WithUser, WithApp, WithMedia, TestCase):

    def test_get(self):

        dataset = self.create_dataset()

        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        response = self.client.get(reverse('datasets:download_datasets_csv', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 200)

        self.assertTrue(os.path.isfile(response['X-Sendfile']))
        
