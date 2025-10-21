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

from localcosmos_server.models import ServerContentImage

from localcosmos_server.template_content.Templates import Template

from localcosmos_server.tests.common import (test_settings,)

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithServerContentImage

from localcosmos_server.template_content.utils import PUBLISHED_IMAGE_TYPE_PREFIX

from .mixins import WithTemplateContent, PAGE_TEMPLATE_TYPE, TEST_TEMPLATE_NAME

import os, uuid


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
        self.assertTrue(hasattr(self.template_content, 'template'))
        self.assertEqual(self.template_content.template, None)

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
    def test_get_component_template_stream(self):
        content_key = 'stream'

        component_template = self.template_content.get_component_template(content_key, 'TestComponent')
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
        

     
class TestLocalizedTemplateContent(WithServerContentImage, WithMedia, WithTemplateContent, WithUser,
                                   WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    @test_settings
    def test_create(self):
        draft_title = 'draft title'
        language = self.app_secondary_languages[0]
        ltc = LocalizedTemplateContent.objects.create(self.user, self.template_content, language,
                                                      draft_title)
        
        self.assertEqual(ltc.created_by, self.user)
        self.assertEqual(ltc.template_content, self.template_content)
        self.assertEqual(ltc.language, 'en')
        self.assertEqual(ltc.draft_title, draft_title)
    
    
    @test_settings
    def test_generate_slug_base(self):
        draft_title = 'äöü'
        
        slug_base = LocalizedTemplateContent.objects.generate_slug_base(draft_title)
        
        self.assertEqual(slug_base, 'aou')
    
    
    @test_settings
    def test_generate_slug(self):
        
        draft_title = 'äöü'
        
        slug = LocalizedTemplateContent.objects.generate_slug(draft_title)
        
        self.assertEqual(slug, 'aou')
        
        ltc = self.create_localized_template_content(self.user, draft_title=draft_title)
        
        self.assertEqual(ltc.slug, 'aou')
        
        slug_2 = LocalizedTemplateContent.objects.generate_slug(draft_title)
        self.assertEqual(slug_2, 'aou-2')
    
    
    @test_settings
    def test_translation_complete(self):
        
        translation_errors = self.primary_ltc.translation_complete()
        
        self.assertEqual(len(translation_errors), 2)
        
        self.primary_ltc.draft_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            },
            'component': [
                {
                    'uuid': str(uuid.uuid4()),
                    'text': 'component text',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': self.primary_ltc.slug,
                        'templateName': self.primary_ltc.template_content.draft_template_name,
                        'title': self.primary_ltc.published_title,
                        'url': '/test-url/', # just for testing
                    }
                }
            ]
        }
        
        self.primary_ltc.save()
        
        translation_errors = self.primary_ltc.translation_complete()
        
        self.assertEqual(len(translation_errors), 0)
        
        # check secondary language
        ltc = self.create_localized_template_content(self.user, language='en')
        
        translation_errors_ltc = ltc.translation_complete()
        
        self.assertEqual(len(translation_errors_ltc), 1)
        self.assertIn('language en', translation_errors_ltc[0])
        
        # with draft contents
        ltc.draft_contents = {
            'longText': 'test text which is a bit longer',
        }
        
        ltc.save()
        
        translation_errors_ltc = ltc.translation_complete()
        
        self.assertEqual(len(translation_errors_ltc), 1)
        self.assertIn('language en', translation_errors_ltc[0])
        
    
    @test_settings
    def test_translation_is_complete(self):
        self.assertFalse(self.primary_ltc.translation_is_complete)
        
        self.primary_ltc.draft_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            },
            'component': [
                {
                    'uuid': str(uuid.uuid4()),
                    'text': 'component text',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': self.primary_ltc.slug,
                        'templateName': self.primary_ltc.template_content.draft_template_name,
                        'title': self.primary_ltc.published_title,
                        'url': '/test-url/', # just for testing
                    }
                }
            ]
        }
        
        self.primary_ltc.save()
        
        self.assertTrue(self.primary_ltc.translation_is_complete)
    
    
    @test_settings
    def test_publish_components(self):
        
        component_uuid = str(uuid.uuid4())
        
        self.primary_ltc.draft_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            },
            'component': [
                {
                    'uuid': component_uuid,
                    'text': 'component text',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': self.primary_ltc.slug,
                        'templateName': self.primary_ltc.template_content.draft_template_name,
                        'title': self.primary_ltc.published_title,
                        'url': '/test-url/', # just for testing
                    }
                }
            ]
        }
        
        self.primary_ltc.save()
        
        image_type = 'component:{}:image'.format(component_uuid)
        content_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        
        self.primary_ltc.publish_components()
        
        published_image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, image_type)
        published_image = self.primary_ltc.image(published_image_type)
        
        self.assertTrue(published_image != None)
        
    
    @test_settings
    def test_publish_images(self):
        
        image_type = 'image' # the content_key, the key of the "contents" dict of TestPage.json
        
        published_image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, image_type)
        published_image = self.primary_ltc.image(published_image_type)
        self.assertEqual(published_image, None)
        
        content_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        template = self.primary_ltc.template_content.draft_template
        template.load_template_and_definition_from_files()
        content_definition = template.definition['contents']['image']
        
        self.primary_ltc.publish_images(image_type, content_definition)
        
        published_image = self.primary_ltc.image(published_image_type)
        
        self.assertTrue(published_image != None)
        
    
    @test_settings
    def test_publish_toplevel_images(self):
        
        image_type = 'image' # the content_key, the key of the "contents" dict of TestPage.json
        
        published_image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, image_type)
        published_image = self.primary_ltc.image(published_image_type)
        self.assertEqual(published_image, None)
        
        content_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        
        self.primary_ltc.publish_toplevel_images()
        
        published_image = self.primary_ltc.image(published_image_type)
        
        self.assertTrue(published_image != None)
    
    
    @test_settings
    def test_publish(self):
        
        component_uuid = str(uuid.uuid4())
        
        self.primary_ltc.draft_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            },
            'component': [
                {
                    'uuid': component_uuid,
                    'text': 'component text',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': self.primary_ltc.slug,
                        'templateName': self.primary_ltc.template_content.draft_template_name,
                        'title': self.primary_ltc.published_title,
                        'url': '/test-url/', # just for testing
                    }
                }
            ]
        }
        
        self.primary_ltc.save()
        
        image_type = 'image' # the content_key, the key of the "contents" dict of TestPage.json
        toplevel_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        published_image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, image_type)
        
        component_image_type = 'component:{}:image'.format(component_uuid)
        component_image = self.get_content_image(self.user, self.primary_ltc, component_image_type)
        published_component_image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, component_image_type)
        
        self.primary_ltc.publish()
        
        published_image = self.primary_ltc.image(published_image_type)
        self.assertTrue(published_image != None)
        
        published_component_image = self.primary_ltc.image(published_component_image_type)
        
        self.assertTrue(published_component_image != None)
        
        self.assertEqual(self.primary_ltc.draft_contents, self.primary_ltc.published_contents)
        self.assertEqual(self.primary_ltc.published_version, self.primary_ltc.draft_version)
        self.assertTrue(self.primary_ltc.published_at != None)
    
    
    @test_settings
    def test_save(self):
        
        self.primary_ltc.draft_version = 3
        self.primary_ltc.save()
        
        ltc = self.create_localized_template_content(self.user, language='en')
        
        self.assertEqual(ltc.draft_version, 3)
        
        self.primary_ltc.published_version = 3
        self.primary_ltc.save(published=True)
        
        self.primary_ltc.refresh_from_db()
        
        self.assertEqual(self.primary_ltc.draft_version, 3)
        self.assertEqual(self.primary_ltc.published_version, 3)
        
        self.primary_ltc.save()
        
        self.primary_ltc.refresh_from_db()
        
        self.assertEqual(self.primary_ltc.draft_version, 4)
        self.assertEqual(self.primary_ltc.published_version, 3)
        
    
    @test_settings
    def test_get_frontend_specific_url(self):
        url = self.primary_ltc.get_frontend_specific_url()
        self.assertEqual(url, '/pages/test-page/test-template-content/')
        
    
    @test_settings
    def test_get_component(self):
        
        component_uuid = str(uuid.uuid4())
        component_2_uuid = str(uuid.uuid4())
        
        component = {
            'uuid': component_uuid,
            'text': 'component text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            }
        }
        
        component_2 = {
            'uuid': component_2_uuid,
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url-2/', # just for testing
            }
        }
        
        stream_item = {
            'uuid': str(uuid.uuid4()),
            'templateName': 'TestComponent',
            'text': 'stream item text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url-3/', # just for testing
            }
        }
        
        self.primary_ltc.draft_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            },
            'component': [
                component,
            ],
            'component2': component_2,
            'stream': [
                stream_item,
            ]
        }
        
        self.primary_ltc.save()
        
        fetched_component = self.primary_ltc.get_component('component', component_uuid)
        self.assertEqual(component, fetched_component)
        
        fetched_component_2 = self.primary_ltc.get_component('component2', component_2_uuid)
        self.assertEqual(component_2, fetched_component_2)
        
        fetched_component_3 = self.primary_ltc.get_component('component3', str(uuid.uuid4()))
        self.assertEqual({}, fetched_component_3)
        
        fetched_stream_item = self.primary_ltc.get_component('stream', stream_item['uuid'])
        self.assertEqual(stream_item, fetched_stream_item)

    @test_settings
    def test_add_or_update_component(self):
        
        component_uuid = str(uuid.uuid4())
        component_2_uuid = str(uuid.uuid4())
        
        component = {
            'uuid': component_uuid,
            'text': 'component text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            }
        }
        
        component_2 = {
            'uuid': component_2_uuid,
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url-2/', # just for testing
            }
        }
        
        stream_item = {
            'uuid': str(uuid.uuid4()),
            'templateName': 'TestComponent',
            'text': 'stream item text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url-3/', # just for testing
            }
        }
        
        self.primary_ltc.add_or_update_component('component', component, save=False)
        
        self.primary_ltc.refresh_from_db()
        
        fetched_component = self.primary_ltc.get_component('component', component_uuid)
        self.assertEqual(fetched_component, {})
        
        self.primary_ltc.add_or_update_component('component', component)
        
        self.primary_ltc.refresh_from_db()
        
        fetched_component = self.primary_ltc.get_component('component', component_uuid)
        self.assertEqual(fetched_component, component)
        
        component['text'] = 'updated text'
        
        self.primary_ltc.add_or_update_component('component', component)
        
        self.primary_ltc.refresh_from_db()
        
        fetched_component = self.primary_ltc.get_component('component', component_uuid)
        self.assertEqual(fetched_component['text'], 'updated text')
        
        # add non list component
        self.primary_ltc.add_or_update_component('component2', component_2)
        self.primary_ltc.refresh_from_db()
        
        fetched_component_2 = self.primary_ltc.get_component('component2', component_2_uuid)
        self.assertEqual(fetched_component_2, component_2)
        
        # stream item
        self.primary_ltc.add_or_update_component('stream', stream_item)
        self.primary_ltc.refresh_from_db()
        fetched_stream_item = self.primary_ltc.get_component('stream', stream_item['uuid'])
        self.assertEqual(fetched_stream_item, stream_item)
        
        updated_stream_item = stream_item.copy()
        updated_stream_item['text'] = 'updated stream item text'
        
        self.primary_ltc.add_or_update_component('stream', updated_stream_item)
        self.primary_ltc.refresh_from_db()
        fetched_stream_item = self.primary_ltc.get_component('stream', stream_item['uuid'])
        self.assertEqual(fetched_stream_item['text'], 'updated stream item text')
            
    
    @test_settings
    def test_remove_component(self):
        
        list_component_uuid = str(uuid.uuid4())
        list_component_2_uuid = str(uuid.uuid4())
        
        single_component_uuid = str(uuid.uuid4())
        
        list_component = {
            'uuid': list_component_uuid,
            'text': 'component text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            }
        }
        
        list_component_2 = {
            'uuid': list_component_2_uuid,
            'text': 'component text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url/', # just for testing
            }
        }
        
        single_component = {
            'uuid': single_component_uuid,
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url-2/', # just for testing
            }
        }
        
        stream_item = {
            'uuid': str(uuid.uuid4()),
            'templateName': 'TestComponent',
            'text': 'stream item text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': self.primary_ltc.published_title,
                'url': '/test-url-3/', # just for testing
            }
        }
        
        self.primary_ltc.add_or_update_component('component', list_component)
        self.primary_ltc.add_or_update_component('component', list_component_2)
        self.primary_ltc.add_or_update_component('component2', single_component)
        self.primary_ltc.add_or_update_component('stream', stream_item)
        
        self.primary_ltc.remove_component('component', list_component_uuid, save=False)
        self.primary_ltc.refresh_from_db()
        
        fetched_list_component = self.primary_ltc.get_component('component', list_component_uuid)
        self.assertEqual(list_component, fetched_list_component)
        
        fetched_list_component_2 = self.primary_ltc.get_component('component',
            list_component_2_uuid)
        self.assertEqual(list_component_2, fetched_list_component_2)
        
        fetched_single_component = self.primary_ltc.get_component('component2',
            single_component_uuid)
        self.assertEqual(single_component, fetched_single_component)
        
        
        self.primary_ltc.remove_component('component', list_component_uuid)
        
        fetched_list_component = self.primary_ltc.get_component('component', list_component_uuid)
        self.assertEqual({}, fetched_list_component)
        
        fetched_list_component_2 = self.primary_ltc.get_component('component',
            list_component_2_uuid)
        self.assertEqual(list_component_2, fetched_list_component_2)
        
        fetched_single_component = self.primary_ltc.get_component('component2',
            single_component_uuid)
        self.assertEqual(single_component, fetched_single_component)
        
        
        self.primary_ltc.remove_component('component2', single_component_uuid)
        
        fetched_list_component = self.primary_ltc.get_component('component', list_component_uuid)
        self.assertEqual({}, fetched_list_component)
        
        fetched_list_component_2 = self.primary_ltc.get_component('component',
            list_component_2_uuid)
        self.assertEqual(list_component_2, fetched_list_component_2)
        
        fetched_single_component = self.primary_ltc.get_component('component2',
            single_component_uuid)
        self.assertEqual({}, fetched_single_component)
        
        # remove stream item
        self.primary_ltc.remove_component('stream', stream_item['uuid'])
        fetched_stream_item = self.primary_ltc.get_component('stream', stream_item['uuid'])
        self.assertEqual({}, fetched_stream_item)
        
    @test_settings
    def test_get_content_image_restrictions(self):
        
        restrictions = self.primary_ltc.get_content_image_restrictions('image')
        
        self.assertFalse(restrictions['allow_cropping'])
        self.assertFalse(restrictions['allow_features'])
    
    
    @test_settings
    def test_str(self):
        
        self.assertEqual(str(self.primary_ltc), self.primary_ltc.draft_title)
        
        
class WithNavigation:
    
    def create_navigation(self):
        nav_type = 'main'
        language = 'de'
        nav_name = 'Test nav'
        nav = Navigation.objects.create(self.app, nav_type, language, nav_name)
        
        return nav
    
    def create_navigation_entry(self, navigation, language, link_name, parent=None):
        
        entry = NavigationEntry(
            navigation=navigation,
            parent=parent
        )
        
        entry.save()
        
        localized_entry = LocalizedNavigationEntry(
            navigation_entry=entry,
            language=language,
            link_name=link_name,
        )
        
        localized_entry.save()
        
        return entry, localized_entry
    
class TestNavigation(WithNavigation, WithTemplateContent, WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
    
    @test_settings
    def test_create(self):
        nav_type = 'main'
        language = 'de'
        nav_name = 'Test nav'
        nav = Navigation.objects.create(self.app, nav_type, language, nav_name)
        
        self.assertEqual(nav.app, self.app)
        self.assertEqual(nav.navigation_type, nav_type)
        
        locale = nav.get_locale(language)
        
        self.assertEqual(locale.name, nav_name)
    
    @test_settings
    def test_nav_settings(self):
        nav = self.create_navigation()
        
        expected_settings = {
            'name': 'Main navigation',
            'maxLevels': 2
        }
        
        self.assertEqual(expected_settings, nav.settings)
        
    
    @test_settings
    def test_toplevel_entries(self):
        nav = self.create_navigation()
        
        entry_1 = NavigationEntry(
            navigation=nav,
        )
        
        entry_1.save()
        
        entry_2 = NavigationEntry(
            navigation=nav,
            parent=entry_1,
        )
        
        entry_2.save()
        
        self.assertEqual(nav.toplevel_entries.count(), 1)
        self.assertEqual(nav.toplevel_entries[0], entry_1)
    
    
    @test_settings
    def test_get_locale(self):
        
        nav = self.create_navigation()
        
        locale = nav.get_locale('de')
        
        self.assertEqual(locale.navigation, nav)
        self.assertEqual(locale.language, 'de')
        
        locale_en = nav.get_locale('en')
        self.assertEqual(locale_en, None)
    
    
    @test_settings
    def test_check_version(self):
        
        nav = self.create_navigation()
        
        locale = nav.get_locale('de')
        
        locale.draft_version = 2
        locale.published_version = 2
        locale.save(published=True)
        
        locale.refresh_from_db()
        self.assertEqual(locale.draft_version, 2)
        self.assertEqual(locale.draft_version, locale.published_version)
        
        nav.check_version()
        
        locale.refresh_from_db()
        self.assertEqual(locale.draft_version, 3)
        self.assertEqual(locale.published_version, 2)
    
    
    @test_settings
    def test_str(self):
        
        nav = self.create_navigation()
        
        locale = nav.get_locale('de')
        
        self.assertEqual(str(nav), locale.name)
        
        locale.delete()
        
        self.assertEqual(str(nav), 'main')
        
        
class TestLocalizedNavigation(WithNavigation, WithTemplateContent, WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
    
    @test_settings
    def test_create(self):
        
        nav = self.create_navigation()
        name = 'nav en'
        language = 'en'
        locale = LocalizedNavigation.objects.create(nav, language, name)
        
        locale.refresh_from_db()
        self.assertEqual(locale.name, name)
        self.assertEqual(locale.navigation, nav)
        self.assertEqual(locale.language, language)
    
    @test_settings
    def test_travel_tree(self):
        
        nav = self.create_navigation()
        
        link_1_name = 'link name'
        link_2_name = 'link 2 name'
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', link_1_name)
        entry_2, locale_2 = self.create_navigation_entry(nav, 'de', link_2_name, entry_1)
        
        
        tree_list = []
        
        for result in travel_tree([entry_1]):
            tree_list.append(result)
            
        expected_list = [
            {
                'child': entry_1,
                'path': [0]
            },
            {
                'child': entry_2,
                'path': [0, 0]
            }
        ]
        
        self.assertEqual(expected_list, tree_list)
    
    
    @test_settings
    def test_serialize(self):
        
        nav = self.create_navigation()
        locale_nav = nav.get_locale('de')
        
        link_1_name = 'link name'
        link_2_name = 'link 2 name'
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', link_1_name)
        entry_2, locale_2 = self.create_navigation_entry(nav, 'de', link_2_name, entry_1)
        
        serialized = locale_nav.serialize()
        
        expected_list = [
            {
                'linkName': 'link name',
                'link_name': 'link name',
                'url': None,
                'children': [
                    {
                        'linkName': 'link 2 name',
                        'link_name': 'link 2 name',
                        'url': None,
                        'children': []
                    }
                ]
            }
        ]
        
        self.assertEqual(serialized, expected_list)
    
    
    @test_settings
    def test_translation_complete(self):
        
        nav = self.create_navigation()
        nav_de = nav.get_locale('de')
        
        nav_de_complete = nav_de.translation_complete()
        self.assertEqual(nav_de_complete, [])
        
        nav_en = LocalizedNavigation(
            navigation = nav,
            language = 'en',
            name = 'main'
        )
        
        nav_en.save()
        
        nav_en_complete = nav_en.translation_complete()
        self.assertEqual(nav_en_complete, [])
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'link_1_name')
        
        nav_en_complete = nav_en.translation_complete()
        self.assertEqual(nav_en_complete, ['The translation for the language en is incomplete.'])
    
    
    @test_settings
    def test_translation_is_complete(self):
        
        nav = self.create_navigation()
        nav_de = nav.get_locale('de')
    
        self.assertTrue(nav_de.translation_is_complete)
        
        nav_en = LocalizedNavigation(
            navigation = nav,
            language = 'en',
            name = 'main'
        )
        
        nav_en.save()
        
        self.assertTrue(nav_en.translation_is_complete)
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'link_1_name')
        
        self.assertFalse(nav_en.translation_is_complete)
    
    
    @test_settings
    def test_publish(self):
        
        nav = self.create_navigation()
        locale_nav = nav.get_locale('de')
        
        link_1_name = 'link name'
        link_2_name = 'link 2 name'
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', link_1_name)
        entry_2, locale_2 = self.create_navigation_entry(nav, 'de', link_2_name, entry_1)
        
        serialized = locale_nav.serialize()
        
        self.assertEqual(locale_nav.published_navigation, None)
        self.assertEqual(locale_nav.published_version, None)
        
        locale_nav.publish()
        
        locale_nav.refresh_from_db()
        self.assertEqual(locale_nav.published_navigation, serialized)
        self.assertEqual(locale_nav.draft_version, locale_nav.published_version)
        
    
    @test_settings
    def test_save(self):
        
        nav = self.create_navigation()
        nav_de = nav.get_locale('de')
        nav_de.draft_version = 5
        nav_de.save()
        
        nav_en = LocalizedNavigation(
            navigation = nav,
        )
        
        nav_en.save()
        self.assertEqual(nav_en.draft_version, 5)
        
        nav_de.publish()
        
        self.assertEqual(nav_de.published_version, 5)
        self.assertEqual(nav_de.draft_version, 5)
        
        nav_de.save()
        
        self.assertEqual(nav_de.published_version, 5)
        self.assertEqual(nav_de.draft_version, 6)
        
        
class TestNavigationEntry(WithNavigation, WithTemplateContent, WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()    
    
    @test_settings
    def test_children(self):
        nav = self.create_navigation()
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'link_1_name')
        entry_2, locale_2 = self.create_navigation_entry(nav, 'de', 'link_2_name', entry_1)
        entry_3, locale_3 = self.create_navigation_entry(nav, 'de', 'link_3_name', entry_2)
        
        self.assertEqual(list(entry_1.children), [entry_2])
    
    @test_settings
    def test_descendants(self):
        
        nav = self.create_navigation()
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'link_1_name')
        entry_2, locale_2 = self.create_navigation_entry(nav, 'de', 'link_2_name', entry_1)
        entry_3, locale_3 = self.create_navigation_entry(nav, 'de', 'link_3_name', entry_2)
        
        self.assertEqual(list(entry_1.descendants), [entry_2, entry_3])
    
    @test_settings
    def test_get_locale(self):
        nav = self.create_navigation()
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'link_1_name')
        
        self.assertEqual(entry_1.get_locale('de'), locale_1)
    
    @test_settings
    def test_str(self):
        
        nav = self.create_navigation()
        
        name_1 = 'link_1_name'
        name_2 = 'link_2_name'
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', name_1)
        locale_2 = LocalizedNavigationEntry(
            navigation_entry=entry_1,
            language='en',
            link_name=name_2,
        )
        locale_2.save()
        
        self.assertEqual(str(entry_1), name_1)
        
    
    @test_settings
    def test_save(self):
        
        nav = self.create_navigation()
        locale_nav = nav.get_locale('de')
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'name_1')
        
        locale_nav.publish()
        
        self.assertEqual(locale_nav.draft_version, 1)
        self.assertEqual(locale_nav.published_version, 1)
        
        entry_1.save()
        
        locale_nav.refresh_from_db()
        self.assertEqual(locale_nav.draft_version, 2)
        self.assertEqual(locale_nav.published_version, 1)
        

class TestLocalizedNavigationEntry(WithNavigation, WithTemplateContent, WithUser, WithApp,
                                   TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    @test_settings
    def test_get_template_content_url(self):
        
        nav = self.create_navigation()
        locale_nav = nav.get_locale('de')
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'name_1')
        
        entry_1.template_content = self.template_content
        entry_1.save()
        
        self.assertEqual(locale_1.get_template_content_url(), '/pages/test-page/test-template-content/')
    
    @test_settings
    def test_serialize(self):
        
        nav = self.create_navigation()
        locale_nav = nav.get_locale('de')
        
        entry_1, locale_1 = self.create_navigation_entry(nav, 'de', 'name_1')
        
        locale_1.url = '/test/url/'
        
        locale_1.save()
        
        expected_output = {
            'linkName': 'name_1',
            'link_name': 'name_1',
            'url': '/test/url/',
            'children': []
        }

        serialized = locale_1.serialize()
        
        self.assertEqual(serialized, expected_output)
        
        entry_1.template_content = self.template_content
        entry_1.save()
        
        expected_output_2 = {
            'linkName': 'name_1',
            'link_name': 'name_1',
            'url': '/pages/test-page/test-template-content/',
            'children': []
        }

        serialized_2 = locale_1.serialize()
        
        self.assertEqual(serialized_2, expected_output_2)
    