###################################################################################################################
#
# TESTS FOR MODELS
# - this file only covers settings.LOCALCOSMOS_PRIVATE == True
#
###################################################################################################################
from django.conf import settings
from django.test import TestCase

from localcosmos_server.template_content.models import (get_published_template_content_root,
    get_published_page_template_path, get_published_page_template_definition_path,
    get_published_component_templates_root, TemplateContent, LocalizedTemplateContent, Navigation,
    LocalizedNavigation, travel_tree, NavigationEntry, LocalizedNavigationEntry)

from localcosmos_server.template_content.Templates import Template

from localcosmos_server.tests.common import (test_settings,)

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia

import os

PAGE_TEMPLATE_TYPE = 'page'
TEST_TEMPLATE_NAME = 'TestPage'
TEST_PAGE_CONTENT_KEYS = ['image', 'longText', 'component', 'text']
TEST_PAGE_CONTENT_TYPES = {
    'image': 'image',
    'longText': 'text',
    'component': 'component',
    'text': 'text',
}

class WithTemplateContent:

    def setUp(self):
        super().setUp()
        self.template_content_title = 'Test template content'
        self.template_content = TemplateContent.objects.create(self.user, self.app,
            self.app.primary_language, self.template_content_title, TEST_TEMPLATE_NAME, PAGE_TEMPLATE_TYPE)


class TestHelperFunctions(WithTemplateContent, WithUser, WithApp, TestCase):

    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()

    @test_settings
    def test_get_published_template_content_root(self):
        
        path = get_published_template_content_root(self.template_content)
        #print(path)
        expected_tail = 'localcosmos-server/template-content/published/test-page-{0}'.format(self.template_content.pk)
        self.assertTrue(path.endswith(expected_tail))

    @test_settings
    def test_get_published_page_template_path(self):
        
        path = get_published_page_template_path(self.template_content, 'template.html')
        # eg localcosmos-server/template-content/published/test-page-3/templates/page/TestPage.html
        #print(path)
        root = get_published_template_content_root(self.template_content)
        expected_path = '{0}/templates/page/TestPage.html'.format(root)
        self.assertEqual(path, expected_path)

    @test_settings
    def test_get_published_page_template_definition_path(self):
        
        path = get_published_page_template_definition_path(self.template_content, 'template.json')
        #print(path)
        root = get_published_template_content_root(self.template_content)
        expected_path = '{0}/templates/page/TestPage.json'.format(root)
        self.assertEqual(path, expected_path)

    @test_settings
    def test_get_published_component_templates_root(self):
        
        components_root = get_published_component_templates_root(self.template_content)
        #print(components_root)
        root = get_published_template_content_root(self.template_content)
        expected_tail = '{0}/templates/component'.format(root)
        self.assertTrue(components_root.endswith(expected_tail))



class TestTemplateContentManager(WithUser, WithApp, TestCase):

    template_content_title = 'Test template content'

    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()

    @test_settings
    def test_create(self):
        template_content = TemplateContent.objects.create(self.user, self.app,
            self.app.primary_language, self.template_content_title, TEST_TEMPLATE_NAME, PAGE_TEMPLATE_TYPE)
        
        self.assertEqual(template_content.app, self.app)
        self.assertEqual(template_content.template_type, PAGE_TEMPLATE_TYPE)
        self.assertEqual(template_content.assignment, None)
        self.assertEqual(template_content.draft_template_name, TEST_TEMPLATE_NAME)
        self.assertEqual(template_content.published_template, None)
        self.assertEqual(template_content.published_template_definition, None)


    @test_settings
    def test_filter_by_taxon(self):
        pass


class TestTemplateContent(WithMedia, WithTemplateContent, WithUser, WithApp, TestCase):

    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()

    @test_settings
    def test_init(self):
        # unpublished
        self.assertTrue(isinstance(self.template_content.draft_template, Template))
        self.assertFalse(hasattr(self.template_content, 'template'))

        # published
        self.template_content.publish_assets()

        published_tc = TemplateContent.objects.get(pk=self.template_content.pk)
        self.assertTrue(isinstance(published_tc.draft_template, Template))
        self.assertTrue(hasattr(published_tc, 'template'))
        self.assertTrue(isinstance(published_tc.template, Template))

    @test_settings
    def test_get_component_template(self):
        content_key = 'component'
        component_template = self.template_content.get_component_template(content_key)
        self.assertTrue(isinstance(component_template, Template))

    @test_settings
    def test_get_published_component_template(self):
        self.template_content.publish_assets()
        published_tc = TemplateContent.objects.get(pk=self.template_content.pk)
        content_key = 'component'
        component_template = published_tc.get_published_component_template(content_key)
        self.assertTrue(isinstance(component_template, Template))

    @test_settings
    def test_get_published_component_template_definition_filepath(self):
        self.template_content.publish_assets()
        published_tc = TemplateContent.objects.get(pk=self.template_content.pk)
        component_template_name = 'TestComponent'
        path = published_tc.get_published_component_template_definition_filepath(component_template_name)

        self.assertTrue(path.endswith('TestComponent.json'))
        self.assertTrue(os.path.isfile(path))

    @test_settings
    def test_get_published_component_template_filepath(self):
        self.template_content.publish_assets()
        published_tc = TemplateContent.objects.get(pk=self.template_content.pk)
        component_template_name = 'TestComponent'
        path = published_tc.get_published_component_template_filepath(component_template_name)

        self.assertTrue(path.endswith('TestComponent.html'))
        self.assertTrue(os.path.isfile(path))

    @test_settings
    def test_get_published_component_template_folder(self):
        
        self.template_content.publish_assets()
        published_tc = TemplateContent.objects.get(pk=self.template_content.pk)
        component_template_name = 'TestComponent'
        path = published_tc.get_published_component_template_folder(component_template_name)

        self.assertTrue(os.path.isdir(path))
        self.assertTrue(path.endswith('templates/component/TestComponent'))

    @test_settings
    def test_name(self):
        name = str(self.template_content)
        self.assertEqual(name, 'Test template content')

    @test_settings
    def test_get_locale(self):
        # en is a secondary language, de is primary for the test app
        en = self.template_content.get_locale('en')
        self.assertEqual(en, None)

        ltc = LocalizedTemplateContent.objects.create(self.user, self.template_content, 'en', 'en title')

        en = self.template_content.get_locale('en')
        self.assertEqual(en, ltc)

    @test_settings
    def test_str(self):

        locale = self.template_content.get_locale(self.app.primary_language)
        if locale:
            locale.delete()

        name = str(self.template_content)
        self.assertEqual(name, 'test-page')

        primary_title = 'primary title'
        ltc = LocalizedTemplateContent.objects.create(self.user, self.template_content,
                                                      self.app.primary_language, primary_title)
        
        name = str(self.template_content)
        self.assertEqual(name, primary_title)


    @test_settings
    def test_publish_assets(self):
        relative_root = get_published_template_content_root(self.template_content)
        published_templates_root = os.path.join(settings.MEDIA_ROOT, relative_root)
        self.assertFalse(os.path.isdir(published_templates_root))

        self.template_content.publish_assets()

        relative_definition_path = get_published_page_template_definition_path(self.template_content, 'TestPage.json')
        definition_path = os.path.join(settings.MEDIA_ROOT, relative_definition_path)
        relative_template_path = get_published_page_template_path(self.template_content, 'TestPage.html')
        template_path = os.path.join(settings.MEDIA_ROOT, relative_template_path)

        self.assertTrue(os.path.isdir(published_templates_root))
        self.assertTrue(os.path.isfile(definition_path))
        self.assertTrue(os.path.isfile(template_path))
        self.assertTrue(definition_path.startswith(published_templates_root))
        self.assertTrue(template_path.startswith(published_templates_root))

        # check if the component templates have been stored on disk
        published_component_template_folder = self.template_content.get_published_component_template_folder('TestComponent')
        component_definition_path = os.path.join(published_component_template_folder, 'TestComponent.json')
        component_path = os.path.join(published_component_template_folder, 'TestComponent.html')

        self.assertTrue(os.path.isfile(component_definition_path))
        self.assertTrue(os.path.isfile(component_path))


    @test_settings
    def test_unpublish(self):
        locale = self.template_content.get_locale(self.app.primary_language)
        locale.draft_contents = {
            'longText' : 'long text',
            'text': 'text',
        }
        locale.save()
        errors = locale.translation_complete()
        self.assertEqual(errors, [])
        locale.publish()
        self.assertEqual(locale.published_version, 1)

        self.template_content.unpublish()

        locale.refresh_from_db()
        self.assertEqual(locale.published_version, None)
        self.assertEqual(locale.published_at, None)

    @test_settings
    def test_is_published(self):
        
        self.assertFalse(self.template_content.is_published)
        locale = self.template_content.get_locale(self.app.primary_language)
        locale.draft_contents = {
            'longText' : 'long text',
            'text': 'text',
        }
        locale.save()
        errors = locale.translation_complete()
        self.assertEqual(errors, [])
        locale.publish()

        self.assertTrue(self.template_content.is_published)