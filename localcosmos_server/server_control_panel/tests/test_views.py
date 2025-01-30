from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings
from django.views.generic import TemplateView

from localcosmos_server.tests.common import test_settings

from localcosmos_server.server_control_panel.views import (AppsContextMixin, LCPrivateOnlyMixin, InstallApp,
                    UninstallApp, AppMixin, EditApp, CheckAppApiStatus, ServerControlPanelHome)

from localcosmos_server.models import App, SecondaryAppLanguages

from localcosmos_server.tests.mixins import WithApp, WithUser, WithMedia, CommonSetUp

from localcosmos_server.tests.common import TEST_MEDIA_ROOT

import os, httpretty, json
TEST_INSTALL_APPS_ROOT = os.path.join(TEST_MEDIA_ROOT, 'install_apps')


ROOT = os.path.dirname(os.path.realpath(__file__))
APP_ZIP_PATH = os.path.join(ROOT, 'app_package', 'installable_app.zip')

class AppsContextMixinTest(AppsContextMixin, TemplateView):
    pass

@test_settings
class TestAppsContextMixin(CommonSetUp, WithUser, WithApp, TestCase):

    def test_get_context_data(self):
        
        view = AppsContextMixinTest()

        context = view.get_context_data(**{})

        self.assertEqual(len(context['apps']), 2)


@test_settings
class TestServerControlPanelHome(CommonSetUp, WithUser, WithApp, TestCase):

    def test_get(self):

        response = self.client.get(reverse('server_control_panel:home'))

        self.assertEqual(response.status_code, 200)


class GetViewMixin:

    def get_view(self, view_class, url_name):
        
        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse(url_name, kwargs=url_kwargs))
        request.session = self.client.session
        request.user = self.user

        view = view_class()
        view.request = request
        view.kwargs = url_kwargs

        return view, request
    
    
        
@test_settings
class TestInstallAppAndLCPrivateOnlyMixin(CommonSetUp, GetViewMixin, WithUser, WithApp, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {}

        if self.app:
            url_kwargs['app_uid'] = self.app.uid

        return url_kwargs


    def test_dispatch(self):

        self.app = None

        view, request = self.get_view(InstallApp, 'server_control_panel:install_app')
        
        response = view.dispatch(request, **self.get_url_kwargs())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.app, None)


    def test_dispatch_with_app(self):

        self.app = None

        view, request = self.get_view(InstallApp, 'server_control_panel:install_app')
        
        response = view.dispatch(request, **self.get_url_kwargs())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.app, self.app)


    def test_get_context_data(self):

        self.app = None

        view, request = self.get_view(InstallApp, 'server_control_panel:install_app')
        view.app = None

        context = view.get_context_data(**{})
        self.assertEqual(context['localcosmos_apps_root'], settings.LOCALCOSMOS_APPS_ROOT)
        self.assertFalse(context['success'])
        self.assertEqual(context['app'], None)
        

    def test_get_initial(self):

        view, request = self.get_view(InstallApp, 'server_control_panel:update_app')
        view.app = self.app

        initial = view.get_initial()
        self.assertEqual(initial['url'], self.app.url)


@test_settings
class TestInstallNewApp(WithUser, WithMedia, TestCase):

    app_uid = 'treesofbavaria'

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = self.create_user()
        self.superuser = self.create_superuser()

        self.client.login(username=self.test_superuser_username, password=self.test_password)

    
    def test_form_valid(self):

        qry = App.objects.filter(uid=self.app_uid)

        self.assertFalse(qry.exists())

        with self.settings(LOCALCOSMOS_APPS_ROOT=TEST_INSTALL_APPS_ROOT):

            url = reverse('server_control_panel:install_app')

            with open(APP_ZIP_PATH, 'rb') as fp:

                post_data = {
                    'zipfile' : fp,
                    'url' : 'http://localhost/',
                }

                self.assertEqual(settings.LOCALCOSMOS_APPS_ROOT,TEST_INSTALL_APPS_ROOT)

                response = self.client.post(url, post_data)

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context_data['success'])
            self.assertEqual(response.context_data['errors'], [])

            self.assertTrue(qry.exists())

            app = qry.first()
            self.assertEqual(app.primary_language, 'de')
            secondary_languages = SecondaryAppLanguages.objects.filter(app=app)
            self.assertEqual(len(secondary_languages), 1)
            self.assertEqual(secondary_languages.first().language_code, 'en')

            temp_folder = os.path.join(settings.MEDIA_ROOT, 'apps/tmp')
            self.assertFalse(os.path.isdir(temp_folder))


@test_settings
class TestInstallNewAppUpdate(CommonSetUp, WithUser, WithMedia, TestCase):

    app_uid = 'treesofbavaria'


    def setUp(self):

        self.app = App(
            uuid = '172dd4e9-9bf0-4f56-b6fd-b5e17e4d9415',
            uid = 'treesofbavaria',
            name = 'Trees of Bavaria',
            primary_language = 'de',
            published_version = '1',
            published_version_path = 'app_path',
            url = 'url',
        )
        
        self.app.save()

        super().setUp()


    def tearDown(self):
        self.app.delete()
        super().tearDown()

    
    def test_form_valid(self):

        qry = App.objects.filter(uid=self.app.uid)

        self.assertTrue(qry.exists())

        to_delete_language = 'jp'
        secondary_language_jp = SecondaryAppLanguages(
            app=qry.first(),
            language_code=to_delete_language,
        )

        secondary_language_jp.save()

        with self.settings(LOCALCOSMOS_APPS_ROOT=TEST_INSTALL_APPS_ROOT):

            url = reverse('server_control_panel:update_app', kwargs={'app_uid': self.app.uid})

            with open(APP_ZIP_PATH, 'rb') as fp:

                post_data = {
                    'zipfile' : fp,
                    'url' : 'http://localhost/',
                }

                self.assertEqual(settings.LOCALCOSMOS_APPS_ROOT,TEST_INSTALL_APPS_ROOT)

                response = self.client.post(url, post_data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['errors'], [])
            self.assertTrue(response.context_data['success'])

            self.assertTrue(qry.exists())

            app = qry.first()
            self.assertEqual(app.primary_language, 'de')
            secondary_languages = SecondaryAppLanguages.objects.filter(app=app)
            self.assertEqual(len(secondary_languages), 1)
            self.assertEqual(secondary_languages.first().language_code, 'en')

            temp_folder = os.path.join(settings.MEDIA_ROOT, 'apps/tmp')
            self.assertFalse(os.path.isdir(temp_folder))


    def test_update_invalid_uid(self):
        
        self.app.uid = 'edited'
        self.app.save()

        qry = App.objects.filter(uid='edited')

        self.assertTrue(qry.exists())

        with self.settings(LOCALCOSMOS_APPS_ROOT=TEST_INSTALL_APPS_ROOT):

            url = reverse('server_control_panel:update_app', kwargs={'app_uid': self.app.uid})

            with open(APP_ZIP_PATH, 'rb') as fp:

                post_data = {
                    'zipfile' : fp,
                    'url' : 'http://localhost/',
                }

                self.assertEqual(settings.LOCALCOSMOS_APPS_ROOT,TEST_INSTALL_APPS_ROOT)

                response = self.client.post(url, post_data)

                self.assertEqual(len(response.context_data['errors']), 1)
                self.assertFalse(response.context_data['success'])


@test_settings
class TestUninstallApp(CommonSetUp, WithUser, WithApp, WithMedia, TestCase):


    def test_get(self):
        url_kwargs = {
            'pk' : self.app.id,
        }
        response = self.client.get(reverse('server_control_panel:uninstall_app', kwargs=url_kwargs), {},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
    

@test_settings
class TestEditAppAndAppMixin(CommonSetUp, GetViewMixin, WithUser, WithApp, WithMedia, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        return url_kwargs
    

    def test_dispatch(self):

        view, request = self.get_view(EditApp, 'server_control_panel:edit_app')
        
        response = view.dispatch(request, **self.get_url_kwargs())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.app, self.app)
        self.assertEqual(response.context_data['app'], self.app)
        

    def test_get_form_kwargs(self):

        view, request = self.get_view(EditApp, 'server_control_panel:edit_app')
        view.app = self.app

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['instance'], self.app)

    
    def test_form_valid(self):

        view, request = self.get_view(EditApp, 'server_control_panel:edit_app')
        view.app = self.app

        new_url = 'http://newhost.local/'

        post_data = {
            'url' : new_url,
        }

        form = view.form_class(data=post_data, instance=self.app)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['app'], self.app)
        self.assertTrue(response.context_data['success'])

        self.app.refresh_from_db()
        self.assertEqual(self.app.url, new_url)

        
@test_settings
class TestCheckAppApiStatus(CommonSetUp, GetViewMixin, WithUser, WithApp, WithMedia, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        return url_kwargs
    

    def test_check_api_status(self):

        # mock http://localhost:8080/api/
        api_url = 'http://localhost:8080/api/'
        httpretty.register_uri(httpretty.GET, api_url,
            body=json.dumps({'success':True}), content_type='application/json',)

        with httpretty.enabled(allow_net_connect=False):

            view, request = self.get_view(CheckAppApiStatus, 'server_control_panel:app_api_status')
            view.app = self.app

            result = view.check_api_status()

            

    def test_get_context_data(self):

        # mock http://localhost:8080/api/
        api_url = 'http://localhost:8080/api/'
        httpretty.register_uri(httpretty.GET, api_url,
            body=json.dumps({'success':True}), content_type='application/json',)

        with httpretty.enabled(allow_net_connect=False):

            view, request = self.get_view(CheckAppApiStatus, 'server_control_panel:app_api_status')
            view.app = self.app

            context = view.get_context_data(**{})
            self.assertIn('api_check', context)
