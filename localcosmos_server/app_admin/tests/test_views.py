from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.app_admin.views import (AdminHome, UserList, ManageAppUserRole, SearchAppUser,
                                                HUMAN_INTERACTION_CLASSES, ManageServerSeoParameters)

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser, WithObservationForm, ViewTestMixin

from localcosmos_server.models import AppUserRole

import json

@test_settings
class TestAdminHome(WithApp, WithUser, WithObservationForm, TestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        self.user = self.create_user()

        self.role = AppUserRole(
            app=self.app,
            user = self.user,
            role='admin',
        )

        self.superuser = self.create_superuser()

        self.role.save()

        self.observation_form = self.create_observation_form()
        

    def test_get_context_data(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        request = self.factory.get(reverse('appadmin:home', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session

        view = AdminHome()        
        view.request = request

        context = view.get_context_data()
            
        self.assertEqual(len(context['review_datasets']), 0)
        self.assertEqual(len(context['no_taxon_datasets']), 0)


    def test_get_context_data_with_datasets(self):
        dataset = self.create_dataset(self.observation_form)

        dataset.validation_step = HUMAN_INTERACTION_CLASSES[0]
        dataset.save()

        dataset_notaxon = self.create_dataset(self.observation_form, taxon=None)
        dataset_notaxon.save()

        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        request = self.factory.get(reverse('appadmin:home', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session

        view = AdminHome()        
        view.request = request

        context = view.get_context_data()
            
        self.assertEqual(context['review_datasets'].first(), dataset)
        self.assertEqual(context['no_taxon_datasets'].first(), dataset_notaxon)

    def test_get(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
        }


        response = self.client.get(reverse('appadmin:home', kwargs=url_kwargs))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('log_in'), response.url)

        
        self.client.login(username=self.test_username, password=self.test_password)
        response_2 = self.client.get(reverse('appadmin:home', kwargs=url_kwargs))
        self.assertEqual(response_2.status_code, 200)

        # expert access
        self.role.role = 'expert'
        self.role.save()

        response_3 = self.client.get(reverse('appadmin:home', kwargs=url_kwargs))
        self.assertEqual(response_3.status_code, 200)

        # no access
        self.role.delete()
        response_4 = self.client.get(reverse('appadmin:home', kwargs=url_kwargs))
        self.assertEqual(response_4.status_code, 403)


@test_settings
class TestUserList(WithUser, WithApp, TestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        self.user = self.create_user()

        self.role = AppUserRole(
            app=self.app,
            user = self.user,
            role='admin',
        )

        self.role.save()

        self.superuser = self.create_superuser()

        self.client.login(username=self.test_superuser_username, password=self.test_password)


    def test_get_context_data_AND_get(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        request = self.factory.get(reverse('appadmin:user_list', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session

        view = UserList()        
        view.request = request

        # one admin
        context = view.get_context_data()
            
        self.assertEqual(context['app_admins'].first().user, self.user)
        self.assertEqual(len(context['app_experts']), 0)
        self.assertEqual(len(context['app_users']), 0)

        self.assertIn('search_app_user_form', context)
        
        response = self.client.get(reverse('appadmin:user_list', kwargs=url_kwargs))
        self.assertEqual(response.status_code, 200)
        
        # one expert
        self.role.role = 'expert'
        self.role.save()
        
        context = view.get_context_data()
            
        self.assertEqual(context['app_experts'].first().user, self.user)
        self.assertEqual(len(context['app_admins']), 0)
        self.assertEqual(len(context['app_users']), 0)

        response_2 = self.client.get(reverse('appadmin:user_list', kwargs=url_kwargs))
        self.assertEqual(response_2.status_code, 200)

        # one user
        self.role.delete()

        request.user = self.superuser

        context = view.get_context_data()
            
        self.assertEqual(len(context['app_experts']), 0)
        self.assertEqual(len(context['app_admins']), 0)
        self.assertEqual(context['app_users'].first(), self.user)

        response_3 = self.client.get(reverse('appadmin:user_list', kwargs=url_kwargs))
        self.assertEqual(response_3.status_code, 200)



@test_settings
class TestManageAppUserRole(WithUser, WithApp, TestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        self.user = self.create_user()

        self.role = AppUserRole(
            app=self.app,
            user = self.user,
            role='admin',
        )

        self.role.save()

        self.superuser = self.create_superuser()

        self.client.login(username=self.test_superuser_username, password=self.test_password)


    def get_view(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
            'user_id' : self.user.id,
        }
        request = self.factory.get(reverse('appadmin:manage_app_user_role', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        view = ManageAppUserRole()
        view.request = request
        view.kwargs = url_kwargs

        return view


    def test_dispatch(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'user_id' : self.user.id,
        }
        request = self.factory.get(reverse('appadmin:manage_app_user_role', kwargs=url_kwargs))
        request.user = self.user
        request.app = self.app
        request.session = self.client.session
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        view = ManageAppUserRole()
        view.request = request
        
        response = view.dispatch(request, **url_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.user, self.user)
        self.assertEqual(view.user_role, self.role)
        

    def test_get_initial(self):

        view = self.get_view()
        
        view.user = self.user
        view.user_role = self.role
        initial = view.get_initial()

        self.assertEqual(initial['role'], self.role.role)

        view.user_role = None
        initial = view.get_initial()

        self.assertEqual(initial['role'], 'user')


    def test_get_context_data(self):

        view = self.get_view()
        
        view.user = self.user
        view.user_role = self.role

        context = view.get_context_data(**{})

        self.assertEqual(context['app_user'], self.user)
        

    def test_form_valid(self):

        view = self.get_view()
        
        view.user = self.user
        view.user_role = self.role

        post_data = {
            'role' : 'expert',
        }

        form = view.form_class(post_data)
        self.assertTrue(form.is_valid())
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)

        self.role.refresh_from_db()
        self.assertEqual(self.role.role, 'expert')
        self.assertEqual(response.context_data['new_role'], 'expert')
        self.assertEqual(response.context_data['success'], True)
        

    def test_get(self):

        view_kwargs = {
            'app_uid' : self.app.uid,
            'user_id' : self.user.id,
        }

        response = self.client.get(reverse('appadmin:manage_app_user_role', kwargs=view_kwargs), {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


    def test_post(self):

        view_kwargs = {
            'app_uid' : self.app.uid,
            'user_id' : self.user.id,
        }

        self.assertEqual(self.role.role, 'admin')
        
        post_data = {
            'role' : 'expert'
        }
        response = self.client.post(reverse('appadmin:manage_app_user_role', kwargs=view_kwargs), post_data,
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.role.refresh_from_db()
        self.assertEqual(self.role.role, 'expert')


        post_data = {
            'role' : 'user'
        }
        response = self.client.post(reverse('appadmin:manage_app_user_role', kwargs=view_kwargs), post_data,
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertFalse(AppUserRole.objects.filter(app=self.app, user=self.user).exists())


@test_settings
class TestSearchAppUser(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.user = self.create_user()

        self.role = AppUserRole(
            app=self.app,
            user = self.user,
            role='admin',
        )

        self.role.save()

        self.superuser = self.create_superuser()

        self.client.login(username=self.test_superuser_username, password=self.test_password)

    def test_get(self):

        view_kwargs = {
            'app_uid' : self.app.uid,
        }

        get_data = {
            'searchtext' : 'test',
        }

        response = self.client.get(reverse('appadmin:search_app_user', kwargs=view_kwargs), {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

        response = self.client.get(reverse('appadmin:search_app_user', kwargs=view_kwargs), get_data,
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content[0]['name'], self.user.username)

    
class TestManageServerSeoParameters(WithApp, WithUser, ViewTestMixin, TestCase):
    
    url_name = 'appadmin:manage_server_seo_parameters'
    view_class = ManageServerSeoParameters
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        
        self.content_type = ContentType.objects.get_for_model(self.user)
        self.object = self.user
        super().setUp()
        
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_type_id' : self.content_type.id,
            'object_id' : self.object.id,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        view = super().get_view()
        view.app = self.app
        return view
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.set_instances(**self.get_url_kwargs())
        self.assertEqual(view.content_type, self.content_type)
        self.assertEqual(view.object_id, self.object.id)
        self.assertEqual(view.instance, self.object)
        self.assertEqual(view.model_class, self.content_type.model_class())
        self.assertEqual(view.seo_parameters, None)
        
        
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.set_instances(**self.get_url_kwargs())
        initial = view.get_initial()
        
        self.assertEqual(initial, {})
        
        # Test with existing SEO parameters
        seo_parameters = ManageServerSeoParameters.seo_model_class(
            content_type=self.content_type,
            object_id=self.object.id,
            title='Test Title',
            meta_description='Test Description'
        )
        seo_parameters.save()
        
        view.seo_parameters = seo_parameters
        initial = view.get_initial()
        
        self.assertEqual(initial, {'title': 'Test Title', 'meta_description': 'Test Description'})
        
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.set_instances(**self.get_url_kwargs())
        context = view.get_context_data()
        
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['app'], self.app)
        self.assertEqual(context['instance'], self.object)
        self.assertEqual(context['seo_parameters'], None)
        self.assertEqual(context['success'], False)
        
        # Test with existing SEO parameters
        seo_parameters = ManageServerSeoParameters.seo_model_class(
            content_type=self.content_type,
            object_id=self.object.id,
            title='Test Title',
            meta_description='Test Description'
        )
        seo_parameters.save()
        
        view.seo_parameters = seo_parameters
        context = view.get_context_data()
        
        self.assertEqual(context['instance'], self.object)
        self.assertEqual(context['seo_parameters'], seo_parameters)
        
    @test_settings
    def test_form_valid(self):
        view = self.get_view()
        view.set_instances(**self.get_url_kwargs())
        
        form_data = {
            'title': 'Test Title',
            'meta_description': 'Test Description'
        }
        
        form = ManageServerSeoParameters.form_class(form_data)
        form.is_valid()
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        # Check if the SEO parameters were created/updated
        seo_parameters = ManageServerSeoParameters.seo_model_class.objects.get(
            content_type=self.content_type,
            object_id=self.object.id
        )
        
        self.assertEqual(seo_parameters.title, 'Test Title')
        self.assertEqual(seo_parameters.meta_description, 'Test Description')

    
    @test_settings
    def test_create_update_delete(self):

        user_content_type = ContentType.objects.get_for_model(self.user)
        
        view = self.get_view()
        view.set_instances(**view.kwargs)
        
        kwargs = {
            'language' : 'en'
        }
        
        post_data = {
            'title' : 'Test title',
            'meta_description' : 'Test description',
            'input_language' : 'en',
        }
        
        form = view.form_class(data=post_data, **kwargs)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        # create
        seo_instance = view.create_update_delete(form.cleaned_data)
        self.assertEqual(seo_instance.title, post_data['title'])
        self.assertEqual(seo_instance.meta_description, post_data['meta_description'])
        self.assertEqual(seo_instance.object_id, self.user.id)
        self.assertEqual(seo_instance.content_type, user_content_type)
        
        # update
        post_data['title'] = 'Updated title'
        post_data['meta_description'] = 'Updated description'
        form = view.form_class(data=post_data, **kwargs)
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        updated_seo_instance = view.create_update_delete(form.cleaned_data)
        
        self.assertEqual(updated_seo_instance.title, post_data['title'])
        self.assertEqual(updated_seo_instance.meta_description, post_data['meta_description'])
        self.assertEqual(updated_seo_instance.object_id, self.user.id)
        self.assertEqual(updated_seo_instance.content_type, user_content_type)
        self.assertEqual(updated_seo_instance.pk, seo_instance.pk)
        
        # delete
        post_data = {
            'input_language' : 'en',
        }
        
        form = view.form_class(data=post_data, **kwargs)
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        deleted_seo_instance = view.create_update_delete(form.cleaned_data)
        self.assertEqual(deleted_seo_instance, None)
        exists = ManageServerSeoParameters.seo_model_class.objects.filter(
            content_type=user_content_type,
            object_id=self.user.id
        ).exists()
        self.assertFalse(exists)