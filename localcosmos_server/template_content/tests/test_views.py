from django.test import TestCase, RequestFactory, Client
from django.urls import reverse

from localcosmos_server.tests.mixins import (WithApp, WithUser, WithMedia, ViewTestMixin,
                                             WithServerContentImage, WithImageForForm)

from localcosmos_server.tests.common import test_settings, test_settings_app_kit

from localcosmos_server.template_content.views import (TemplateContentList, CreateTemplateContent,
        ManageTemplateContentCommon, WithLocalizedTemplateContent, ManageLocalizedTemplateContent,
        ManageComponent, DeleteComponent, TranslateTemplateContent, GetTemplateContentFormFields,
        ManageTemplateContentImage, DeleteTemplateContentImage, ContextFromComponentIdentifier,
        ManageComponentImage, DeleteComponentImage, PublishTemplateContent,
        UnpublishTemplateContent, DeleteTemplateContent, ManageNavigation, PublishNavigation,
        DeleteNavigation, NavigationEntriesMixin, ManageNavigationEntries,
        GetNavigationEntriesTree, ManageNavigationEntry, DeleteNavigationEntry,
        ComponentContentView, TranslateNavigation)


from localcosmos_server.template_content.forms import (CreateTemplateContentForm,
        ManageLocalizedTemplateContentForm, ManageComponentForm,
        TranslateTemplateContentForm)

from localcosmos_server.template_content.models import (LocalizedTemplateContent, Navigation,
    NavigationEntry, LocalizedNavigationEntry, LocalizedNavigation)

from localcosmos_server.template_content.utils import get_component_image_type


from django.contrib.contenttypes.models import ContentType

from .mixins import WithTemplateContent, TEST_TEMPLATE_NAME, PAGE_TEMPLATE_TYPE

import uuid, json

class TestTemplateContentList(WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'template_content_home'
    view_class = TemplateContentList
    
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        
        return url_kwargs
    
    
    @test_settings_app_kit
    def test_get_context_data(self):
        
        view = self.get_view()
        view.app = self.app
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertTrue(context['supports_navigations'])
        self.assertEqual(context['navigations'], [])
        self.assertEqual(list(context['localized_template_contents']), [])
        
        required_home_page = {
            'assignment' : 'home',
            'template_content' : None,
            'template_type': 'page',
        }
        required_footer_feature = {
            'assignment' : 'footer',
            'template_content' : None,
            'template_type': 'feature',
        }
        
        self.assertEqual(context['required_offline_contents'], [required_home_page, required_footer_feature])
        
        
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.app = self.app
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertTrue(context['supports_navigations'])
        self.assertEqual(list(context['navigations']), [])
        self.assertEqual(list(context['localized_template_contents']), [])
        
        self.assertEqual(context['required_offline_contents'], [])
        
        
class TestCreateTemplateContent(WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'create_template_content'
    view_class = CreateTemplateContent
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_type': 'page',
        }
        
        return url_kwargs
    
    @test_settings
    def test_get_contex_data(self):
        
        view = self.get_view()
        view.app = self.app
        
        context = view.get_context_data()
        self.assertEqual(context['template_type'], 'page')
        self.assertEqual(context['assignment'], None)
        
    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        view.app = self.app
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['language'], 'de')
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        view.app = self.app
        
        form = view.get_form()
        
        self.assertTrue(isinstance(form, CreateTemplateContentForm))
    
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'draft_title': 'draft test page',
            'template_name': 'TestPage',
            'input_language': 'de',
        }
        
        form = CreateTemplateContentForm(self.app, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        view = self.get_view()
        view.app = self.app
        
        response = view.form_valid(form)
        
        ltc = LocalizedTemplateContent.objects.all().last()
        
        self.assertEqual(ltc.created_by, view.request.user)
        self.assertEqual(ltc.language, 'de')
        self.assertEqual(ltc.draft_title, 'draft test page')
        self.assertEqual(ltc.template_content.assignment, None)
        self.assertEqual(ltc.template_content.template_type, 'page')
        
        url_kwargs = {
            'app_uid': self.app.uid,
            'localized_template_content_id': ltc.pk,
        }
        expected_url = reverse('manage_localized_template_content', kwargs=url_kwargs)
        
        self.assertEqual(response['location'], expected_url)
        self.assertEqual(response.status_code, 302)
    
    
class TestCreateTemplateContentAssignment(WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'create_template_content'
    view_class = CreateTemplateContent
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_type': 'page',
            'assignment': 'home',
        }
        
        return url_kwargs
    
    @test_settings
    def test_get_contex_data(self):
        
        view = self.get_view()
        view.app = self.app
        
        context = view.get_context_data()
        self.assertEqual(context['template_type'], 'page')
        self.assertEqual(context['assignment'], 'home')
        
        
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'draft_title': 'draft test page',
            'template_name': 'TestPage',
            'input_language': 'de',
        }
        
        form = CreateTemplateContentForm(self.app, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        view = self.get_view()
        view.app = self.app
        
        response = view.form_valid(form)
        
        ltc = LocalizedTemplateContent.objects.all().last()
        
        self.assertEqual(ltc.created_by, view.request.user)
        self.assertEqual(ltc.language, 'de')
        self.assertEqual(ltc.draft_title, 'draft test page')
        self.assertEqual(ltc.template_content.assignment, 'home')
        self.assertEqual(ltc.template_content.template_type, 'page')
        
        url_kwargs = {
            'app_uid': self.app.uid,
            'localized_template_content_id': ltc.pk,
        }
        expected_url = reverse('manage_localized_template_content', kwargs=url_kwargs)
        
        self.assertEqual(response['location'], expected_url)
        self.assertEqual(response.status_code, 302)
        

class TestManageLocalizedTemplateContent(WithTemplateContent, WithUser, WithApp, ViewTestMixin,
                                         TestCase):
    
    url_name = 'manage_localized_template_content'
    view_class = ManageLocalizedTemplateContent
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'localized_template_content_id': self.primary_ltc.pk,
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_template_content(**view.kwargs)
        
        return view
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        form = view.get_form()
        self.assertTrue(isinstance(form, ManageLocalizedTemplateContentForm))
    
    @test_settings
    def test_get_form_kwargs(self):
        
        view = self.get_view()
        
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['language'], 'de')
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['template_content'], self.template_content)
        self.assertEqual(context['language'], 'de')
        self.assertEqual(context['preview_url'], 'http://pages/test-page/test-template-content/')
    
    @test_settings
    def test_get_preview_url(self):
        
        view = self.get_view()
        
        preview_url = view.get_preview_url()
        self.assertEqual(preview_url, 'http://pages/test-page/test-template-content/')
    
    @test_settings
    def test_get_iniital(self):
        
        self.primary_ltc.draft_contents = {
            'text' : 'test text'
        }
        
        self.primary_ltc.save()
        
        view = self.get_view()
        
        initial = view.get_initial()
        
        self.assertEqual(initial['draft_title'], self.primary_ltc.draft_title)
        self.assertEqual(initial['input_language'], 'de')
        self.assertEqual(initial['text'], 'test text')
        
    
    @test_settings
    def test_get_updated_content_dict(self):
        
        template_definition = self.template_content.draft_template.definition
        
        self.primary_ltc.draft_contents = {
            'text': 'draft test text',
            'longText': 'draft longer text',
        }
        
        self.primary_ltc.publish()
        
        post_data = {
            'input_language': 'de',
            'draft_title': 'title',
            'text': 'test text',
            'longText': 'longer text',
            'link': self.primary_ltc.pk,
        }
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content,
                                localized_template_content=self.primary_ltc, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        existing_dict = {
            'text': 'old text',
            'deprecated': 'dep',
            'image': 'image mock',
            'component': 'component mock',
        }
        
        view = self.get_view()
        new_dict = view.get_updated_content_dict(template_definition, existing_dict, form)
        
        expected_new_dict = {
            'text': 'test text', 
            'image': 'image mock',
            'component': 'component mock',
            'longText': 'longer text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'Test template content',
                'url': '/pages/TestPage/test-template-content/'
            }
        }

        self.assertEqual(new_dict, expected_new_dict)
        
    
    @test_settings
    def test_save_localized_template_content(self):
        
        post_data = {
            'input_language': 'de',
            'draft_title': 'some title',
            'text': 'test text',
            'longText': 'longer text',
            'link': '',
        }
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content,
                                localized_template_content=self.primary_ltc, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        view = self.get_view()
        view.save_localized_template_content(form)
        
        self.primary_ltc.refresh_from_db()
        
        self.assertEqual(self.primary_ltc.draft_title, 'some title')
        
        expected_contents = {
            'text': 'test text',
            'longText': 'longer text'
        }
        self.assertEqual(self.primary_ltc.draft_contents, expected_contents)
    
    
    @test_settings
    def test_set_template_content(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_template_content(**view.kwargs)
        
        self.assertEqual(view.localized_template_content, self.primary_ltc)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.language, 'de')
    
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        
        post_data = {
            'input_language': 'de',
            'draft_title': 'title 2',
            'text': 'test text',
            'longText': 'longer text',
            'link': '',
        }
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content,
                                localized_template_content=self.primary_ltc, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        self.primary_ltc.refresh_from_db()
        
        self.assertEqual(self.primary_ltc.draft_title, 'title 2')
        
        expected_contents = {
            'text': 'test text',
            'longText': 'longer text'
        }
        self.assertEqual(self.primary_ltc.draft_contents, expected_contents)
        

class TestManageComponent(WithTemplateContent, WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'add_component'
    view_class = ManageComponent
    content_key = 'component'
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'localized_template_content_id': self.primary_ltc.pk,
            'content_key': self.content_key,
        }
        
        return url_kwargs
    
    
    def get_post_data(self, language, uuid):
        
        post_data = {
            'component_input_language': language,
            'component_uuid': uuid,
            'component_text': 'component text',
            'component_link': self.primary_ltc.pk,
        }
        
        return post_data
        
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_template_content(**view.kwargs)
        view.set_primary_language()
        view.set_component(**view.kwargs)
        
        return view
    
    
    @test_settings
    def test_set_template_content(self):
        
        view = super().get_view()
        view.set_template_content(**view.kwargs)
        self.assertEqual(view.localized_template_content, self.primary_ltc)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.language, self.primary_ltc.language)
    
    @test_settings
    def test_set_component(self):
        
        view = super().get_view()
        view.set_template_content(**view.kwargs)
        view.set_component(**view.kwargs)
        self.assertEqual(view.app, self.app)
        self.assertEqual(view.component_uuid, None)
        self.assertEqual(view.content_key, self.content_key)
        self.assertEqual(view.component, {})
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(type(initial['uuid']), type(uuid.uuid4()))
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['content_key'], self.content_key)
        self.assertEqual(context['component'], {})
    
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        form = view.get_form()
        
        self.assertTrue(isinstance(form, ManageComponentForm))
        
        
    def get_expected_draft_contents(self, uuid):
        
        expected_draft_contents = {
            'text': 'draft test text',
            'longText': 'draft longer text',
            'component': [
                {
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'url': '/pages/TestPage/test-template-content/',
                        'slug': 'test-template-content',
                        'title': 'Test template content',
                        'templateName': 'TestPage'
                    },
                    'text': 'component text',
                    'uuid': str(uuid),
                    'templateName': 'TestComponent'
                }
            ]
        }
        
        return expected_draft_contents
    
    @test_settings
    def test_form_valid(self):
        
        # otherwise link wont work
        self.primary_ltc.draft_contents = {
            'text': 'draft test text',
            'longText': 'draft longer text',
        }
        
        self.primary_ltc.publish()
        
        view = self.get_view()
        
        initial = view.get_initial()
        
        # the form uses add_prefix
        post_data = self.get_post_data(view.primary_language, initial['uuid'])
        
        component_template_name = 'TestComponent'
        
        form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
            self.content_key, component_template_name, initial=initial, data=post_data)
        
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])
        
        self.primary_ltc.refresh_from_db()
        
        expected_draft_contents = self.get_expected_draft_contents(initial['uuid'])

        self.assertEqual(self.primary_ltc.draft_contents, expected_draft_contents)


class TestAddStreamItem(TestManageComponent):
    
    url_name = 'add_component'
    view_class = ManageComponent
    content_key = 'stream'
    
    ajax = True
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'localized_template_content_id': self.primary_ltc.pk,
            'content_key': self.content_key,
            'component_template_name': 'TestComponent'
        }
        
        return url_kwargs
    
    
    def get_post_data(self, language, uuid):
        
        post_data = {
            'stream_input_language': language,
            'stream_uuid': uuid,
            'stream_text': 'component text',
            'stream_link': self.primary_ltc.pk,
        }
        
        return post_data
    
    def get_expected_draft_contents(self, uuid):
        
        expected_draft_contents = {
            'text': 'draft test text',
            'longText': 'draft longer text',
            'stream': [
                {
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'url': '/pages/TestPage/test-template-content/',
                        'slug': 'test-template-content',
                        'title': 'Test template content',
                        'templateName': 'TestPage'
                    },
                    'text': 'component text',
                    'uuid': str(uuid),
                    'templateName': 'TestComponent'
                }
            ]
        }
        
        return expected_draft_contents
    
    
class WithExistingComponent:
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        self.primary_ltc.draft_contents = {
            'text': 'draft test text',
            'longText': 'draft longer text',
        }
        
        self.primary_ltc.save()
        
        self.primary_ltc.publish()
        
        
        self.component_uuid = str(uuid.uuid4())
        
        self.component = {
            'link': {
                'pk': str(self.primary_ltc.pk),
                'url': '/pages/TestPage/test-template-content/',
                'slug': 'test-template-content',
                'title': 'Test template content',
                'templateName': 'TestPage'
            },
            'text': 'component text',
            'uuid': self.component_uuid,
        }
        
        self.primary_ltc.draft_contents['component'] = [self.component]
        self.primary_ltc.save()
        
        
class TestManageExistingComponent(WithExistingComponent, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'manage_component'
    view_class = ManageComponent
    content_key = 'component'
    
    ajax = True

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'localized_template_content_id': self.primary_ltc.pk,
            'content_key': self.content_key,
            'component_uuid': self.component_uuid
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_template_content(**view.kwargs)
        view.set_primary_language()
        view.set_component(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_component(self):
        
        view = super().get_view()
        view.set_template_content(**view.kwargs)
        view.set_component(**view.kwargs)
        self.assertEqual(view.app, self.app)
        self.assertEqual(view.component_uuid, self.component_uuid)
        self.assertEqual(view.content_key, self.content_key)
        self.assertEqual(view.component, self.component)
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['uuid'], self.component_uuid)
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['content_key'], self.content_key)
        self.assertEqual(context['component'], self.component)
    
     
    @test_settings
    def test_get_form(self):
        view = self.get_view()
        form = view.get_form()
        
        self.assertTrue(isinstance(form, ManageComponentForm))
    
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        
        initial = view.get_initial()
        
        post_data = {
            'component_input_language': view.primary_language,
            'component_uuid': initial['uuid'],
            'component_text': 'component text updated',
            'component_link': self.primary_ltc.pk,
        }
        
        component_template_name = 'TestComponent'
        
        form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
            self.content_key, component_template_name, initial=initial, data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])
        
        self.primary_ltc.refresh_from_db()
        
        expected_draft_contents = {
            'text': 'draft test text',
            'longText': 'draft longer text',
            'component': [
                {
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'url': '/pages/TestPage/test-template-content/',
                        'slug': 'test-template-content',
                        'title': 'Test template content',
                        'templateName': 'TestPage'
                    },
                    'text': 'component text updated',
                    'uuid': str(post_data['component_uuid']),
                    'templateName': 'TestComponent'
                }
            ]
        }

        self.assertEqual(self.primary_ltc.draft_contents, expected_draft_contents)
        

class TestDeleteComponent(WithExistingComponent, WithTemplateContent, WithUser, WithApp,
                          ViewTestMixin, TestCase):
    
    url_name = 'delete_component'
    view_class = DeleteComponent
    content_key = 'component'
    
    ajax = True    
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'localized_template_content_id': self.primary_ltc.pk,
            'content_key': self.content_key,
            'component_uuid': self.component_uuid
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_component(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_component(self):
        
        view = super().get_view()
        
        view.set_component(**view.kwargs)
        self.assertEqual(view.localized_template_content, self.primary_ltc)
        self.assertEqual(view.content_key, self.content_key)
        self.assertEqual(view.component_uuid, self.component_uuid)
        self.assertEqual(view.component_template_name, 'Card')
        
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['app'], self.app)
        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['content_key'], self.content_key)
        self.assertEqual(context['component_uuid'], self.component_uuid)
        self.assertEqual(context['component_template_name'], 'Card')
        self.assertEqual(context['deleted'], False)
    
    
    @test_settings
    def test_post(self):
        
        view = self.get_view()
        existing_components = self.primary_ltc.draft_contents['component']
        self.assertEqual(len(existing_components), 1)
        self.assertEqual(existing_components[0]['uuid'], self.component_uuid)
        
        response = view.post(None, **view.kwargs)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['deleted'], True)
        
        self.primary_ltc.refresh_from_db()
        self.assertEqual(self.primary_ltc.draft_contents['component'], [])


class TestTranslateTemplateContent(WithExistingComponent, WithTemplateContent, WithUser, WithApp,
                          ViewTestMixin, TestCase):
    
    url_name = 'translate_template_content'
    view_class = TranslateTemplateContent
    content_key = 'component'   
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id': self.template_content.pk,
            'language': 'en',
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_template_content(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_template_content(self):
        
        view = super().get_view()
        view.set_template_content(**view.kwargs)
        
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.language, 'en')
        self.assertEqual(view.localized_template_content, None)
    
    
    @test_settings
    def test_form_valid(self):
        
        new_ltc = self.template_content.get_locale('en')
        self.assertEqual(new_ltc, None)
        
        post_data = {
            'input_language': 'en',
            'draft_title': 'en title 2',
        }
        
        form = TranslateTemplateContentForm(self.app, self.template_content, data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        view = self.get_view()
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        
        
        new_ltc = self.template_content.get_locale('en')
        self.assertEqual(new_ltc.language, 'en')
        self.assertEqual(new_ltc.draft_title, 'en title 2')
        
        # now post with contents
        post_data_2 = {
            'input_language': 'en',
            'draft_title': 'en title 2',
            'text': 'en test text',
            'longText': 'en longer text',
        }
        
        form_2 = TranslateTemplateContentForm(self.app, self.template_content,
                                    localized_template_content=new_ltc, data=post_data_2)
        
        form_2.is_valid()
        
        self.assertEqual(form_2.errors, {})
        
        view_2 = self.get_view()
        
        response_2 = view_2.form_valid(form_2)
        self.assertEqual(response_2.status_code, 200)
        
        new_ltc.refresh_from_db()
        
        expected_draft_contents = {
            'text': 'en test text',
            'longText': 'en longer text',
        }
        
        self.assertEqual(expected_draft_contents, new_ltc.draft_contents)
        

class TestGetTemplateContentFormFields(WithExistingComponent, WithTemplateContent, WithUser,
                                       WithApp, ViewTestMixin, TestCase):
    
    url_name = 'get_template_content_form_fields'
    view_class = GetTemplateContentFormFields
    content_key = 'text'
    
    ajax = True
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid': self.app.uid,
            'localized_template_content_id': self.primary_ltc.pk,
            'content_key': self.content_key,
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_content(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_content(self):
        
        view = super().get_view()
        
        view.set_content(**view.kwargs)
        self.assertEqual(view.localized_template_content, self.primary_ltc)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.app, self.app)
        self.assertEqual(view.content_key, self.content_key)
    
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        
        form = view.get_form()
        
        self.assertEqual(len(form.fields), 1)
        self.assertIn(self.content_key, form.fields)
        


class TestManageTemplateContentImage(WithTemplateContent, WithUser, WithApp, ViewTestMixin,
                                     TestCase):
    
        
    url_name = 'manage_template_content_image'
    view_class = ManageTemplateContentImage
    
    image_type = 'image' # content_key from TestPage.json
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_type_id': self.content_type.pk,
            'object_id': self.primary_ltc.pk,
            'image_type': self.image_type,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_content_image(**view.kwargs)
        view.set_primary_language()
        view.taxon = None
        
        return view
    

    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['app'], self.app)
        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['content_key'], self.image_type)


class TestManageExistingTemplateContentImage(WithTemplateContent, WithServerContentImage,
            WithMedia, WithUser, WithApp, ViewTestMixin, TestCase):
    
    
    url_name = 'manage_template_content_image'
    view_class = ManageTemplateContentImage
    
    image_type = 'image' # content_key from TestPage.json
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
        
        # create the content image
        self.content_image = self.get_content_image(self.superuser, self.primary_ltc,
                                                    image_type=self.image_type)
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_image_id': self.content_image.pk,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_content_image(**view.kwargs)
        view.set_primary_language()
        view.taxon = None
        view.licence_registry_entry = {}
        
        return view
    

    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['app'], self.app)
        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['content_key'], self.image_type)
        


class TestDeleteTemplateContentImage(WithTemplateContent, WithServerContentImage, WithMedia,
                                     WithUser, WithApp, ViewTestMixin, TestCase):
    
    
    url_name = 'delete_template_content_image'
    view_class = DeleteTemplateContentImage
    
    image_type = 'image' # content_key from TestPage.json
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
        
        # create the content image
        self.content_image = self.get_content_image(self.superuser, self.primary_ltc,
                                                    image_type=self.image_type)
        
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.content_image.pk,
        }
        
        return url_kwargs
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.app = self.app
        view.object = self.content_image
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['content_key'], self.image_type)
        

# no saved component, also test compnent creation  
class TestManageComponentImage(WithTemplateContent, WithImageForForm,
            WithServerContentImage, WithMedia, WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'manage_component_image'
    view_class = ManageComponentImage
        
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
        
        self.component_uuid = str(uuid.uuid4())
        # TestComponent.json
        self.image_type = get_component_image_type('component', self.component_uuid, 'image')
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_type_id': self.content_type.pk,
            'object_id': self.primary_ltc.pk,
            'image_type': self.image_type,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_content_image(**view.kwargs)
        view.set_primary_language()
        view.taxon = None
        view.licence_registry_entry = {}
        
        return view
    
    
    @test_settings
    def test_get_image_type(self):
        
        view = self.get_view()
        image_type = view.get_image_type()
        
        expected_image_type = 'component:{0}:image'.format(self.component_uuid)
        self.assertEqual(image_type, expected_image_type)
    
    
    @test_settings
    def test_set_component(self):
        
        view = self.get_view()
        view.set_component()
        
        self.assertEqual(view.content_key, 'image')
        self.assertEqual(view.component_key, 'component')
        self.assertEqual(view.component_uuid, self.component_uuid)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['content_key'], 'image')
        self.assertEqual(context['component_key'], 'component')
        self.assertEqual(context['component_uuid'], self.component_uuid)
    
    @test_settings
    def test_save_image(self):
        
        self.assertEqual(self.primary_ltc.draft_contents, None)
        
        image = self.primary_ltc.image(self.image_type)
        self.assertEqual(image, None)
        
        view = self.get_view()
        
        form_class = view.form_class
        
        
        data = {
            'input_language': view.primary_language,
            'creator_name' : 'Test name',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'crop_parameters': json.dumps({
                'width' : 12,
                'height' : 20,
            }),
            'image_type': self.image_type,
        }

        image = self.get_image('test-image.jpg')
        
        file_dict = {
            'source_image': image
        }
        
        form_kwargs = view.get_form_kwargs()
        form = form_class(data=data, files=file_dict, **form_kwargs)

        form.is_valid()
        self.assertEqual(form.errors, {})
        
        view.save_image(form)
        
        self.primary_ltc.refresh_from_db()
        
        expected_draft_contents = {
            'component': [
                {
                    'uuid': self.component_uuid
                }
            ]
        }
        
        self.assertEqual(self.primary_ltc.draft_contents, expected_draft_contents)
        
        image = self.primary_ltc.image(self.image_type)
        self.assertEqual(image.image_type, self.image_type)
        


class TestManageExistingComponentImage(WithExistingComponent, WithTemplateContent,
        WithImageForForm, WithServerContentImage, WithMedia, WithUser, WithApp,
        ViewTestMixin, TestCase):
    
    url_name = 'manage_component_image'
    view_class = ManageComponentImage
        
    ajax = True
    
    def setUp(self):
        
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
        
        # TestComponent.json
        self.image_type = get_component_image_type('component', self.component['uuid'], 'image')

        # create the content image
        self.content_image = self.get_content_image(self.superuser, self.primary_ltc,
                                                    image_type=self.image_type)
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_image_id': self.content_image.pk,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_content_image(**view.kwargs)
        view.taxon = None
        view.licence_registry_entry = {}
        
        return view
    
    
    @test_settings
    def test_get_image_type(self):
        view = self.get_view()
        
        image_type = view.get_image_type()
        
        self.assertEqual(image_type, self.image_type)
        
        
    @test_settings
    def test_save_image(self):
        
        self.assertEqual(self.primary_ltc.draft_contents['component'][0], self.component)
        
        image_1 = self.primary_ltc.image(self.image_type)
        self.assertEqual(image_1.image_type, self.image_type)
        
        view = self.get_view()
        
        form_class = view.form_class
        
        
        data = {
            'input_language': self.primary_ltc.language,
            'creator_name' : 'Test name',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'crop_parameters': json.dumps({
                'width' : 12,
                'height' : 20,
            }),
            'image_type': self.image_type,
        }

        image = self.get_image('test-image.jpg')
        
        file_dict = {
            'source_image': image
        }
        
        form = form_class(data=data, files=file_dict)
        
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        view.save_image(form)
        
        self.primary_ltc.refresh_from_db()
        
        self.assertEqual(self.primary_ltc.draft_contents['component'][0], self.component)
        
        image_2 = self.primary_ltc.image(self.image_type)
        self.assertEqual(image_1, image_2)
        

class TestDeleteComponentImage(WithExistingComponent, WithTemplateContent,
                WithServerContentImage, WithMedia, WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'delete_component_image'
    view_class = DeleteComponentImage
    
    ajax = True
    
    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
        
        # TestComponent.json
        self.image_type = get_component_image_type('component', self.component['uuid'], 'image')

        # create the content image
        self.content_image = self.get_content_image(self.superuser, self.primary_ltc,
                                                    image_type=self.image_type)
        
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.content_image.pk,
        }
        
        return url_kwargs
    
    
    @test_settings
    def test_get_image_type(self):
        
        view = self.get_view()
        view.object = self.content_image
        
        image_type = view.get_image_type()
        
        self.assertEqual(image_type, self.image_type)
        

    
class TestPublishTemplateContent(WithExistingComponent, WithTemplateContent,
                WithServerContentImage, WithMedia, WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'publish_template_content'
    view_class = PublishTemplateContent
    
    ajax = True
    
    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(LocalizedTemplateContent)
        super().setUp()
        
        # TestComponent.json
        self.image_type = 'image'

        # create the content image
        self.content_image = self.get_content_image(self.superuser, self.primary_ltc,
                                                    image_type=self.image_type)
        
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id': self.template_content.id,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        
        view = super().get_view()
        view.set_template_content(**view.kwargs)
        view.app = self.app
        
        return view
    
    
    @test_settings
    def test_set_template_content(self):
        
        view = super().get_view()
        view.set_template_content(**view.kwargs)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.localized_template_content, self.primary_ltc)
        self.assertEqual(view.language, 'all')
        
    
    @test_settings
    def test_get_context_data_no_en(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['template_content'], self.template_content)
        self.assertEqual(context['publication'], True)
        self.assertEqual(context['publication_errors'], ['Translation for the language en is missing'])        
    
    
    @test_settings
    def test_get_context_data_success(self):
        
        view = self.get_view()
        view.language = 'de'
        
        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['localized_template_content'], self.primary_ltc)
        self.assertEqual(context['template_content'], self.template_content)
        self.assertEqual(context['publication'], True)
        self.assertEqual(context['publication_errors'], [])        
    

class TestUnpublishTemplateContent(WithExistingComponent, WithTemplateContent,
                WithServerContentImage, WithMedia, WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'unpublish_template_content'
    view_class = UnpublishTemplateContent
    
    ajax = True
    
    def setUp(self):
        super().setUp()
        
        
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id': self.template_content.id,
        }
        
        return url_kwargs
    
    
    def get_view(self):
        
        view = super().get_view()
        view.template_content = self.template_content
        view.app = self.app
        
        return view
    
    
    @test_settings
    def test_get_context_data(self):
        
        errors = self.template_content.publish(language='de')
        self.assertEqual(errors, [])
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['template_content'], self.template_content)
        self.assertEqual(context['success'], False)
        
    @test_settings
    def test_post(self):
        
        errors = self.template_content.publish(language='de')
        self.assertEqual(errors, [])
        
        view = self.get_view()
        
        self.assertEqual(self.primary_ltc.published_version, 1)
        
        response = view.post(None, **view.kwargs)
        
        self.assertEqual(response.context_data['success'], True)
        
        self.primary_ltc.refresh_from_db()
        
        self.assertFalse(self.primary_ltc.published_version, None)
        



class TestManageNavigation(WithTemplateContent, WithUser, WithApp, ViewTestMixin, TestCase):
    
    url_name = 'create_template_content_navigation'
    view_class = ManageNavigation
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.primary_language = self.primary_ltc.language
        view.set_navigation(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_navigation(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        self.assertEqual(view.navigation, None)
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['navigation'], None)
        self.assertEqual(context['success'], False)
    
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        initial = view.get_initial()
        
        self.assertEqual(initial, {})
    
    
    @test_settings
    def test_get_form_kwargs(self):
        
        view = self.get_view()
        
        form_kwargs = view.get_form_kwargs()
        
        self.assertEqual(form_kwargs['navigation'], None)
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        
        form = view.get_form()
        
        self.assertEqual(form.__class__.__name__, 'ManageNavigationForm')
    
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'input_language': 'de',
            'name': 'Main nav',
            'navigation_type': 'main',
        }
        
        view = self.get_view()
        
        form = view.form_class(self.app, data=post_data)
        
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        navigation = Navigation.objects.get(app=self.app, navigation_type='main')

        locale = navigation.get_locale('de')
        self.assertEqual(locale.name, 'Main nav')


class TestManageExistingNavigation(WithTemplateContent, WithUser, WithApp, ViewTestMixin,
                                   TestCase):
    
    url_name = 'manage_template_content_navigation'
    view_class = ManageNavigation
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        self.navigation = Navigation.objects.create(self.app, 'main', 'de', 'Main nav')
        self.locale = self.navigation.get_locale('de')
        
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.navigation.pk,
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.primary_language = self.primary_ltc.language
        view.set_navigation(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_navigation(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        self.assertEqual(view.navigation, self.navigation)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(context['success'], False)
    
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        initial = view.get_initial()
        
        expected_initial = {
            'name': self.locale.name,
            'navigation_type': 'main',
        }
        self.assertEqual(initial, expected_initial)
    
    
    @test_settings
    def test_get_form_kwargs(self):
        
        view = self.get_view()
        
        form_kwargs = view.get_form_kwargs()
        
        self.assertEqual(form_kwargs['navigation'], self.navigation)
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        
        form = view.get_form()
        
        self.assertEqual(form.__class__.__name__, 'ManageNavigationForm')
    
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'input_language': 'de',
            'name': 'Main nav edited',
            'navigation_type': 'main',
        }
        
        view = self.get_view()
        self.assertEqual(view.navigation, self.navigation)
        
        form = view.form_class(self.app, navigation=self.navigation, data=post_data)
        
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        navigation = Navigation.objects.get(app=self.app, navigation_type='main')

        locale = navigation.get_locale('de')
        self.assertEqual(locale.name, 'Main nav edited')
        
        
class TestPublishNavigation(WithTemplateContent, WithUser, WithApp, ViewTestMixin,
                                   TestCase):
    
    url_name = 'publish_template_content_navigation'
    view_class = PublishNavigation
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        self.navigation = Navigation.objects.create(self.app, 'main', 'de', 'Main nav')
        self.locale = self.navigation.get_locale('de')
        
        
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'navigation_id': self.navigation.pk,
        }
        
        return url_kwargs
        
        
    def get_view(self):
        
        view = super().get_view()
        view.app = self.app
        view.set_navigation(**view.kwargs)
        
        return view
        
    
    @test_settings
    def test_set_navigation(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        self.assertEqual(view.navigation, self.navigation)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(context['localized_navigation'], self.locale)
        self.assertEqual(context['publication'], True)
        self.assertEqual(context['publication_errors'], ['Translation for the language en is missing'])
        
        view.language = 'de'
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['publication_errors'], [])


class TestDeleteNavigation(WithTemplateContent, WithUser, WithApp, ViewTestMixin,
                                   TestCase):
    
    url_name = 'delete_template_content_navigation'
    view_class = DeleteNavigation
    
    ajax = True
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        self.navigation = Navigation.objects.create(self.app, 'main', 'de', 'Main nav')
        self.locale = self.navigation.get_locale('de')
        
        
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.navigation.pk,
        }
        
        return url_kwargs
    

class WithNavigation:
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        self.navigation = Navigation.objects.create(self.app, 'main', 'de', 'Main nav')
        self.locale = self.navigation.get_locale('de')
        
    def create_navigation_entry(self):
        
        self.nav_entry = NavigationEntry(
            navigation=self.navigation,
        )
        
        self.nav_entry.save()
        
        self.nav_entry_locale = LocalizedNavigationEntry(
            navigation_entry = self.nav_entry,
            language = 'de',
            link_name = 'link name'
        )
        
        self.nav_entry_locale.save()
        
        
class TestManageNavigationEntries(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'manage_template_content_navigation_entries'
    view_class = ManageNavigationEntries
    
    ajax = True
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.navigation.pk,
        }
        
        return url_kwargs
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.app = self.app
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(list(context['navigation_entries']), [])
        
        self.create_navigation_entry()
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(list(context['navigation_entries']), [self.nav_entry])
        

class TestGetNavigationEntriesTree(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'get_template_content_navigation_entries'
    view_class = GetNavigationEntriesTree
    
    ajax = True
    
    def setUp(self):
        super().setUp()
        self.create_navigation_entry()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.navigation.pk,
        }
        
        return url_kwargs
    
    
class TestManageNavigationEntry(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'create_template_content_navigation_entry'
    view_class = ManageNavigationEntry
    
    ajax = True
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'navigation_id': self.navigation.pk,
        }
        
        return url_kwargs
    
    def get_view(self):
        view = super().get_view()
        view.app = self.app
        view.set_navigation(**view.kwargs)
        view.primary_language = self.primary_ltc.language
        return view
    
    @test_settings
    def test_set_navigation(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        self.assertEqual(view.navigation, self.navigation)
        self.assertEqual(view.navigation_entry, None)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(context['navigation_entry'], None)
        self.assertEqual(context['success'], False)
        
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        
        initial = view.get_initial()
        
        expected_initial = {}
        self.assertEqual(initial, expected_initial)
    
    @test_settings
    def test_get_form_kwargs(self):
        
        view = self.get_view()
        
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['navigation_entry'], None)
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        form = view.get_form()
        self.assertEqual(form.__class__.__name__, 'ManageNavigationEntryForm')
    
    @test_settings
    def test_form_valid(self):
        
        
        view = self.get_view()
        
        post_data = {
            'input_language': 'de',
            'link_name': 'test link name'
        }
        
        form = view.form_class(self.navigation, data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        self.assertEqual(len(self.navigation.toplevel_entries), 0)
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        self.navigation.refresh_from_db()
        self.assertEqual(len(self.navigation.toplevel_entries), 1)
        

class TestManageExistingNavigationEntry(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'manage_template_content_navigation_entry'
    view_class = ManageNavigationEntry
    
    ajax = True
    
    def setUp(self):
        super().setUp()
        self.create_navigation_entry()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'navigation_id': self.navigation.pk,
            'pk': self.nav_entry.pk
        }
        
        return url_kwargs
    
    def get_view(self):
        view = super().get_view()
        view.app = self.app
        view.set_navigation(**view.kwargs)
        view.primary_language = self.primary_ltc.language
        return view
    
    
    @test_settings
    def test_set_navigation(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        self.assertEqual(view.navigation, self.navigation)
        self.assertEqual(view.navigation_entry, self.nav_entry)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(context['navigation_entry'], self.nav_entry)
        self.assertEqual(context['success'], False)
        
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        
        initial = view.get_initial()
        
        expected_initial = {
            'link_name': 'link name',
            'parent': None,
            'template_content': None
        }
        self.assertEqual(initial, expected_initial)
    
    @test_settings
    def test_get_form_kwargs(self):
        
        view = self.get_view()
        
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['navigation_entry'], self.nav_entry)
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        form = view.get_form()
        self.assertEqual(form.__class__.__name__, 'ManageNavigationEntryForm')
    
    @test_settings
    def test_form_valid(self):
        
        
        view = self.get_view()
        
        post_data = {
            'input_language': 'de',
            'link_name': 'test link name',
            'template_content': self.primary_ltc.pk,
        }
        
        form = view.form_class(self.navigation, data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        self.assertEqual(len(self.navigation.toplevel_entries), 1)
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        self.navigation.refresh_from_db()
        self.assertEqual(len(self.navigation.toplevel_entries), 1)
        
        self.nav_entry.refresh_from_db()
        self.assertEqual(self.nav_entry.template_content, self.template_content)
    

class TestDeleteNavigationEntry(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'delete_template_content_navigation_entry'
    view_class = DeleteNavigationEntry
    
    ajax = True
    
    def setUp(self):
        super().setUp()
        self.create_navigation_entry()
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.nav_entry.pk
        }
        
        return url_kwargs
    

class TestComponentContentView(WithExistingComponent, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'component_content_view'
    view_class = ComponentContentView
    content_key = 'component'
    
    ajax = True

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id': self.template_content.pk,
            'content_key': self.content_key,
            'component_uuid': self.component_uuid
        }
        
        return url_kwargs
    
    def get_view(self):
        view = super().get_view()
        view.app = self.app
        view.set_template_content(**view.kwargs)
        view.set_component(**view.kwargs)
        return view
    
    @test_settings
    def test_set_template_content(self):
        view = super().get_view()
        
        view.set_template_content(**view.kwargs)
        view.set_component(**view.kwargs)
        
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.app, self.app)
        self.assertEqual(view.language, 'de')
        self.assertEqual(view.localized_template_content, self.primary_ltc)
    

class TestTranslateNavigation(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                  ViewTestMixin, TestCase):
    
    url_name = 'translate_template_content_navigation'
    view_class = TranslateNavigation
    
    ajax = True
    
    def setUp(self):
        super().setUp()
        self.create_navigation_entry()
        
        
    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk': self.navigation.pk,
            'language': 'en',
        }
        
        return url_kwargs
    
    def get_view(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        
        return view
    
    @test_settings
    def test_set_navigation(self):
        
        view = super().get_view()
        view.set_navigation(**view.kwargs)
        self.assertEqual(view.app, self.app)
        self.assertEqual(view.navigation, self.navigation)
        self.assertEqual(view.language, 'en')
        self.assertEqual(view.localized_navigation, None)
        self.assertEqual(view.primary_locale_navigation, self.locale)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['localized_navigation'], None)
        self.assertEqual(context['navigation'], self.navigation)
        self.assertEqual(context['primary_locale_navigation'], self.locale)
        self.assertEqual(context['language'], 'en')
        self.assertEqual(context['saved'], False)
    
    @test_settings
    def test_get_form_kwargs(self):
        
        view = self.get_view()
        
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['language'], 'en')
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial, {})
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        
        form = view.get_form()
        
        self.assertEqual(form.__class__.__name__, 'TranslateNavigationForm')
    
    @test_settings
    def test_save_localized_navigation(self):
        
        view = self.get_view()
        
        view.localized_navigation = LocalizedNavigation.objects.create(self.navigation, 'en',
                                                                       'nav name en')
        
        post_data = {
            'input_language': 'en',
            'name': 'nav name en',
        }
        
        post_data['ne-{0}'.format(self.nav_entry.pk)] = 'nav entry name en'
        
        form = view.form_class(self.app, self.navigation, data=post_data, **view.get_form_kwargs())
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        view.save_localized_navigation(form)
        
        entries = LocalizedNavigationEntry.objects.filter(navigation_entry=self.nav_entry,
                                                          language='en')
        self.assertEqual(len(entries), 1)
        
        self.assertEqual(entries[0].link_name, 'nav entry name en')
        
        post_data = {
            'input_language': 'en',
            'name': 'nave name edited',
        }
        
        post_data['ne-{0}'.format(self.nav_entry.pk)] = ''
        
        form = view.form_class(self.app, self.navigation, data=post_data, **view.get_form_kwargs())
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        view.save_localized_navigation(form)
        
        entries_2 = LocalizedNavigationEntry.objects.filter(navigation_entry=self.nav_entry,
                                                          language='en')
        self.assertEqual(len(entries_2), 0)
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        
        post_data = {
            'input_language': 'en',
            'name': 'nav name en',
        }
        
        post_data['ne-{0}'.format(self.nav_entry.pk)] = 'nav entry name en'
        
        form = view.form_class(self.app, self.navigation, data=post_data, **view.get_form_kwargs())
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['saved'], True)
        
        new_locale = self.navigation.get_locale('en')
        self.assertEqual(new_locale.name, 'nav name en')