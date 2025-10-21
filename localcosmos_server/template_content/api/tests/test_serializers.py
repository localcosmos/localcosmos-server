from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.template_content.tests.mixins import (WithTemplateContent, TEST_TEMPLATE_NAME,
    PAGE_TEMPLATE_TYPE, WithNavigation)

from localcosmos_server.tests.common import (test_settings,)
from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithServerContentImage

from localcosmos_server.template_content.api.serializers import (LocalizedTemplateContentSerializer,
                ContentLicenceSerializer, ContentImageSerializer, LocalizedNavigationSerializer)


from localcosmos_server.template_content.utils import get_component_image_type

from localcosmos_server.models import TaxonomicRestriction
from localcosmos_server.taxonomy.lazy import LazyAppTaxon

import uuid

class LTCPreviewTestsMixin:
    
    def prepare_template_content(self):
        pass
    
    @test_settings
    def test_get_from_definition(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        key = 'templateName'
        
        content_definition = serializer.get_from_definition(self.primary_ltc, key)
        
        # from TestPage.json
        expected_definition = 'test-page'
        
        self.assertEqual(content_definition, expected_definition)
    
    
    @test_settings
    def test_get_template_definition(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_definition = serializer.get_template_definition(self.primary_ltc)
        
        self.assertEqual(template_definition['templateName'], 'test-page')
        self.assertEqual(template_definition['type'], 'page')
        self.assertEqual(template_definition['templatePath'], '/template_content/page/home/home.html')
        self.assertEqual(template_definition['version'], 1)
    
    
    @test_settings
    def test_get_title(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        title = serializer.get_title(self.primary_ltc)
        
        self.assertEqual(title, 'Test template content')
    
    
    @test_settings
    def test_get_templateName(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_name = serializer.get_templateName(self.primary_ltc)
        
        self.assertEqual(template_name, 'test-page')
    
    
    @test_settings
    def test_get_version(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        version = serializer.get_version(self.primary_ltc)
        
        self.assertEqual(version, 1)
    
    
    @test_settings
    def test_get_templatePath(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_path = serializer.get_templatePath(self.primary_ltc)
        
        self.assertEqual(template_path, '/template_content/page/home/home.html')
    
    
    @test_settings
    def test_get_image_data(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_definition = serializer.get_template_definition(self.primary_ltc)
        
        content_key = 'image'
        image_definition = template_definition['contents'][content_key]
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        self.assertEqual(image_data, None)
        
        content_image = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        expected_image_data = {
            'imageUrl': {
                '1x': content_image.image_url(size=250),
                '2x': content_image.image_url(size=500),
                '4x': content_image.image_url(size=1000),
            },
            'licence': {
                'licence': None,
                'licenceVersion': '',
                'creatorName': '',
                'creatorLink': '',
                'sourceLink': ''
            }
        }
        
        self.assertEqual(expected_image_data, image_data)


    @test_settings
    def test_get_image_data_allow_multiple(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_definition = serializer.get_template_definition(self.primary_ltc)
        
        content_key = 'images'
        
        image_definition = template_definition['contents'][content_key]
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        self.assertEqual(image_data, [])
        
        content_image = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        expected_image_data = [{
            'imageUrl': {
                '1x': content_image.image_url(size=250),
                '2x': content_image.image_url(size=500),
                '4x': content_image.image_url(size=1000),
            },
            'licence': {
                'licence': None,
                'licenceVersion': '',
                'creatorName': '',
                'creatorLink': '',
                'sourceLink': ''
            }
        }]
        
        self.assertEqual(expected_image_data, image_data)
    
    
    @test_settings
    def test_add_image_data_to_component(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        component_key = 'component2'
        
        component = self.primary_ltc.draft_contents[component_key]
        
        component_template = self.primary_ltc.template_content.get_component_template(component_key)
        component_definition = component_template.definition
        
        c_w_image_data = serializer.add_image_data_to_component(component_key, component, component_definition,
                                               self.primary_ltc)
        
        expected_output = {
            'uuid': component['uuid'],
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'component 2 link title',
                'url': '/test-url-2/'
            },
            'image': None
        }
        
        self.assertEqual(c_w_image_data, expected_output)
        
        image_type = get_component_image_type(component_key, component['uuid'], 'image')

        content_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        
        c_w_image_data_2 = serializer.add_image_data_to_component(component_key, component, component_definition,
                                               self.primary_ltc)
        
        expected_output_2 = {
            'uuid': component['uuid'],
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'component 2 link title',
                'url': '/test-url-2/'
            },
            'image': {
                'imageUrl': {
                    '1x': content_image.image_url(size=250),
                    '2x': content_image.image_url(size=500),
                    '4x': content_image.image_url(size=1000),
                },
                'licence': {
                    'licence': None,
                    'licenceVersion': '',
                    'creatorName': '',
                    'creatorLink': '',
                    'sourceLink': ''
                }
            }
        }
        
        self.assertEqual(c_w_image_data_2, expected_output_2)
    
    
    @test_settings
    def test_get_contents(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : True
        }
        
        component_key = 'component2'
        component = self.primary_ltc.draft_contents[component_key]
        component_image_type = get_component_image_type(component_key, component['uuid'], 'image')

        component_image = self.get_content_image(self.user, self.primary_ltc, component_image_type)
        
        content_image = self.get_content_image(self.user, self.primary_ltc, 'image')
        
        content_image_multiple = self.get_content_image(self.user, self.primary_ltc, 'images')
        
        multi_component_key = 'component'
        multi_component = self.primary_ltc.draft_contents[multi_component_key][0]
        multi_component_image_type = get_component_image_type(multi_component_key,
                                                              multi_component['uuid'], 'image')

        multi_component_image = self.get_content_image(self.user, self.primary_ltc, multi_component_image_type)
        
        stream_key = 'stream'
        stream_item = self.primary_ltc.draft_contents[stream_key][0]
        stream_item_image_type = get_component_image_type(stream_key, stream_item['uuid'], 'image')
        stream_item_image = self.get_content_image(self.user, self.primary_ltc, stream_item_image_type)
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        contents = serializer.get_contents(self.primary_ltc)
        
        expected_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'link title',
                'url': '/test-url/'
            },
            'component': [
                {
                    'uuid': multi_component['uuid'],
                    'text': 'component text',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': 'test-template-content',
                        'templateName': 'TestPage',
                        'title': 'component link title',
                        'url': '/test-url/'
                    },
                    'image': {
                        'imageUrl': {
                            '1x': multi_component_image.image_url(size=250),
                            '2x': multi_component_image.image_url(size=500),
                            '4x': multi_component_image.image_url(size=1000),
                        },
                        'licence': {
                            'licence': None,
                            'licenceVersion': '',
                            'creatorName': '',
                            'creatorLink': '',
                            'sourceLink': ''
                        }
                    }
                }
            ],
            'component2': {
                'uuid': component['uuid'],
                'text': 'component text 2',
                'link': {
                    'pk': str(self.primary_ltc.pk),
                    'slug': 'test-template-content',
                    'templateName': 'TestPage',
                    'title': 'component 2 link title',
                    'url': '/test-url-2/'
                },
                'image': {
                    'imageUrl': {
                        '1x': component_image.image_url(size=250),
                        '2x': component_image.image_url(size=500),
                        '4x': component_image.image_url(size=1000),
                    },
                    'licence': {
                        'licence': None,
                        'licenceVersion': '',
                        'creatorName': '',
                        'creatorLink': '',
                        'sourceLink': ''
                    }
                },
            },
            'image': {
                'imageUrl': {
                    '1x': content_image.image_url(size=250),
                    '2x': content_image.image_url(size=500),
                    '4x': content_image.image_url(size=1000),
                },
                'licence': {
                    'licence': None,
                    'licenceVersion': '',
                    'creatorName': '',
                    'creatorLink': '',
                    'sourceLink': ''
                }
            },
            'images': [
                {
                    'imageUrl': {
                        '1x': content_image_multiple.image_url(size=250),
                        '2x': content_image_multiple.image_url(size=500),
                        '4x': content_image_multiple.image_url(size=1000),
                    },
                    'licence': {
                        'licence': None,
                        'licenceVersion': '',
                        'creatorName': '',
                        'creatorLink': '',
                        'sourceLink': ''
                    }
                }
            ],
            'stream': [
                {
                    'uuid': stream_item['uuid'],
                    'templateName': 'TestComponent',
                    'text': 'stream item text',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': 'test-template-content',
                        'templateName': 'TestPage',
                        'title': 'stream item link title',
                        'url': '/test-url-3/'
                    },
                    'image': {
                        'imageUrl': {
                            '1x': stream_item_image.image_url(size=250),
                            '2x': stream_item_image.image_url(size=500),
                            '4x': stream_item_image.image_url(size=1000),
                        },
                        'licence': {
                            'licence': None,
                            'licenceVersion': '',
                            'creatorName': '',
                            'creatorLink': '',
                            'sourceLink': ''
                        }
                    }
                }
            ]
        }
        
        for key, value in expected_contents.items():
            self.assertEqual(expected_contents[key], contents[key])
        self.assertEqual(contents, expected_contents)
        
    
    @test_settings
    def test_deserialize(self):
        
        self.prepare_template_content()
        
        component_key = 'component2'
        component = self.primary_ltc.draft_contents[component_key]
        
        multi_component_key = 'component'
        multi_component = self.primary_ltc.draft_contents[multi_component_key][0]
        
        stream_key = 'stream'
        stream_item = self.primary_ltc.draft_contents[stream_key][0]
        
        context = {
            'preview' : True
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        expected_data = {
            'title': 'Test template content',
            'templateName': 'test-page',
            'templatePath': '/template_content/page/home/home.html',
            'version': 1,
            'contents': {
                'longText': 'test text which is a bit longer',
                'text': 'short text',
                'link': {
                    'pk': str(self.primary_ltc.pk),
                    'slug': 'test-template-content',
                    'templateName': 'TestPage',
                    'title': 'link title',
                    'url': '/test-url/'
                },
                'component': [
                    {
                        'uuid': multi_component['uuid'],
                        'text': 'component text',
                        'link': {
                            'pk': str(self.primary_ltc.pk),
                            'slug': 'test-template-content',
                            'templateName': 'TestPage',
                            'title': 'component link title',
                            'url': '/test-url/'
                        },
                        'image': None
                    }
                ],
                'component2': {
                    'uuid': component['uuid'],
                    'text': 'component text 2',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': 'test-template-content',
                        'templateName': 'TestPage',
                        'title': 'component 2 link title',
                        'url': '/test-url-2/'
                    },
                    'image': None
                },
                'image': None,
                'images': [],
                'stream': [
                    {
                        'uuid': stream_item['uuid'],
                        'templateName': 'TestComponent',
                        'text': 'stream item text',
                        'link': {
                            'pk': str(self.primary_ltc.pk),
                            'slug': 'test-template-content',
                            'templateName': 'TestPage',
                            'title': 'stream item link title',
                            'url': '/test-url-3/'
                        },
                        'image': None,
                    }
                ]
            },
            'linkedTaxa': [],
            'linkedTaxonProfiles': [],
        }
        
        self.assertEqual(serializer.data, expected_data)
        
    
    @test_settings
    def test_serialize(self):
        
        self.prepare_template_content()
        # not supported
        pass
    
    @test_settings
    def test_get_linked_taxa(self):
        
        self.prepare_template_content()
        
        test_taxon_kwargs = {
            "taxon_source": "taxonomy.sources.col",
            "name_uuid": "eb53f49f-1f80-4505-9d56-74216ac4e548",
            "taxon_nuid": "006002009001005001001",
            "taxon_latname": "Abies alba",
            "taxon_author" : "Linnaeus",
            "gbif_nubKey": 2685484,
        }
        lazy_taxon = LazyAppTaxon(**test_taxon_kwargs)
        
        template_content = self.primary_ltc.template_content
        
        restriction = TaxonomicRestriction(
            taxon = lazy_taxon,
            content_type = ContentType.objects.get_for_model(template_content),
            object_id = template_content.id,
        )

        restriction.save()
        
        context = {
            'preview' : True
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)

        taxa = serializer.get_linkedTaxa(self.primary_ltc)

        expected_taxa = [
            {
                'nameUuid': 'eb53f49f-1f80-4505-9d56-74216ac4e548',
                'taxonAuthor': 'Linnaeus',
                'taxonLatname': 'Abies alba',
                'taxonNuid': '006002009001005001001',
                'taxonSource': 'taxonomy.sources.col'
            }
        ]

        self.assertEqual(taxa, expected_taxa)


class TestPreviewLocalizedTemplateContentSerializer(LTCPreviewTestsMixin, WithTemplateContent,
                                        WithServerContentImage, WithMedia, WithUser, WithApp, TestCase):
    
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        self.fill_localized_template_content()


class TestPublishedLocalizedTemplateContentSerializer(LTCPreviewTestsMixin, WithTemplateContent,
                                    WithServerContentImage, WithMedia, WithUser, WithApp, TestCase):
    
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
        
        
    def create_published_draft_contents(self):
        
        # fill it with then published contents that differ from draf contents
        self.primary_ltc.draft_title = 'Published title'
        
        component_uuid = str(uuid.uuid4())
        component_2_uuid = str(uuid.uuid4())
        
        component = {
            'uuid': component_uuid,
            'text': 'component text published',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': 'component link title published',
                'url': '/test-url-pc/', # just for testing
            }
        }
        
        component_2 = {
            'uuid': component_2_uuid,
            'text': 'component text 2 published',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': 'component 2 link published title',
                'url': '/test-url-2-pc/', # just for testing
            }
        }
        
        published_contents = {
            'longText': 'published long test text which is a bit longer',
            'text': 'published short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': 'published link title',
                'url': '/test-url-published/', # just for testing
            },
            'component': [
                component,
            ],
            'component2': component_2,
        }
        
        self.primary_ltc.draft_contents = published_contents
        self.primary_ltc.save()
        
        
    def prepare_template_content(self):
        
        self.create_published_draft_contents()
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        self.primary_ltc.refresh_from_db()
        
        # fill it with draft contents
        self.primary_ltc.draft_title = self.template_content_title
        self.fill_localized_template_content()    
    
    @test_settings
    def test_get_published_from_definition(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        key = 'templateName'
        
        content_definition = serializer.get_from_definition(self.primary_ltc, key)
        
        # from TestPage.json
        expected_definition = 'test-page'
        
        self.assertEqual(content_definition, expected_definition)
        
        
    @test_settings
    def test_get_published_template_definition(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False,
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_definition = serializer.get_template_definition(self.primary_ltc)
        
        self.assertEqual(template_definition['templateName'], 'test-page')
        self.assertEqual(template_definition['type'], 'page')
        self.assertEqual(template_definition['templatePath'], '/template_content/page/home/home.html')
        self.assertEqual(template_definition['version'], 1)
        
    
    @test_settings
    def test_get_published_title(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        title = serializer.get_title(self.primary_ltc)
        
        self.assertEqual(title, 'Published title')
        
    
    @test_settings
    def test_get_published_templateName(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_name = serializer.get_templateName(self.primary_ltc)
        
        self.assertEqual(template_name, 'test-page')
    
    
    @test_settings
    def test_get_published_version(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        version = serializer.get_version(self.primary_ltc)
        
        self.assertEqual(version, 1)
        
    
    @test_settings
    def test_get_published_templatePath(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False,
        }
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_path = serializer.get_templatePath(self.primary_ltc)
        
        self.assertEqual(template_path, '/template_content/page/home/home.html')
        
    
    @test_settings
    def test_get_published_image_data(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_definition = serializer.get_template_definition(self.primary_ltc)
        
        content_key = 'image'
        image_definition = template_definition['contents'][content_key]
        
        content_image = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        expected_image_data = {
            'imageUrl': {
                '1x': content_image.image_url(size=250),
                '2x': content_image.image_url(size=500),
                '4x': content_image.image_url(size=1000),
            },
            'licence': {
                'licence': None,
                'licenceVersion': '',
                'creatorName': '',
                'creatorLink': '',
                'sourceLink': ''
            }
        }
        
        self.assertEqual(expected_image_data, image_data)
        
    
    @test_settings
    def test_get_published_image_data_allow_multiple(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        template_definition = serializer.get_template_definition(self.primary_ltc)
        
        content_key = 'images'
        
        image_definition = template_definition['contents'][content_key]
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        self.assertEqual(image_data, [])
        
        content_image = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        
        image_data = serializer.get_image_data(image_definition, self.primary_ltc, content_key)
        
        expected_image_data = [{
            'imageUrl': {
                '1x': content_image.image_url(size=250),
                '2x': content_image.image_url(size=500),
                '4x': content_image.image_url(size=1000),
            },
            'licence': {
                'licence': None,
                'licenceVersion': '',
                'creatorName': '',
                'creatorLink': '',
                'sourceLink': ''
            }
        }]
        
        self.assertEqual(expected_image_data, image_data)
    
       
    @test_settings
    def test_add_published_image_data_to_component(self):
        
        self.prepare_template_content()
        
        context = {
            'preview' : False
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        component_key = 'component2'
        
        component = self.primary_ltc.draft_contents[component_key]
        
        component_template = self.primary_ltc.template_content.get_component_template(component_key)
        component_definition = component_template.definition
        
        c_w_image_data = serializer.add_image_data_to_component(component_key, component, component_definition,
                                               self.primary_ltc)
        
        expected_output = {
            'uuid': component['uuid'],
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'component 2 link title',
                'url': '/test-url-2/'
            },
            'image': None
        }
        
        self.assertEqual(c_w_image_data, expected_output)
        
        image_type = get_component_image_type(component_key, component['uuid'], 'image')

        content_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        
        c_w_image_data_2 = serializer.add_image_data_to_component(component_key, component, component_definition,
                                               self.primary_ltc)
        
        expected_output_2 = {
            'uuid': component['uuid'],
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'component 2 link title',
                'url': '/test-url-2/'
            },
            'image': {
                'imageUrl': {
                    '1x': content_image.image_url(size=250),
                    '2x': content_image.image_url(size=500),
                    '4x': content_image.image_url(size=1000),
                },
                'licence': {
                    'licence': None,
                    'licenceVersion': '',
                    'creatorName': '',
                    'creatorLink': '',
                    'sourceLink': ''
                }
            }
        }
        
        self.assertEqual(c_w_image_data_2, expected_output_2)
        
    
    @test_settings
    def test_get_published_contents(self):
        
        self.create_published_draft_contents()
        
        context = {
            'preview' : False
        }
        
        component_key = 'component2'
        component = self.primary_ltc.draft_contents[component_key]
        component_image_type = get_component_image_type(component_key, component['uuid'], 'image')

        component_image = self.get_content_image(self.user, self.primary_ltc, component_image_type)
        
        content_image = self.get_content_image(self.user, self.primary_ltc, 'image')
        
        content_image_multiple = self.get_content_image(self.user, self.primary_ltc, 'images')
        
        multi_component_key = 'component'
        multi_component = self.primary_ltc.draft_contents[multi_component_key][0]
        multi_component_image_type = get_component_image_type(multi_component_key,
                                                              multi_component['uuid'], 'image')

        multi_component_image = self.get_content_image(self.user, self.primary_ltc, multi_component_image_type)
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        self.primary_ltc.refresh_from_db()
        
        # fill it with draft contents
        self.primary_ltc.draft_title = self.template_content_title
        self.fill_localized_template_content() 
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        contents = serializer.get_contents(self.primary_ltc)
        
        expected_contents = {
            'longText': 'published long test text which is a bit longer',
            'text': 'published short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': 'test-template-content',
                'templateName': 'TestPage',
                'title': 'published link title',
                'url': '/test-url-published/'
            },
            'component': [
                {
                    'uuid': multi_component['uuid'],
                    'text': 'component text published',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': 'test-template-content',
                        'templateName': 'TestPage',
                        'title': 'component link title published',
                        'url': '/test-url-pc/'
                    },
                    'image': {
                        'imageUrl': {
                            '1x': multi_component_image.image_url(size=250),
                            '2x': multi_component_image.image_url(size=500),
                            '4x': multi_component_image.image_url(size=1000),
                        },
                        'licence': {
                            'licence': None,
                            'licenceVersion': '',
                            'creatorName': '',
                            'creatorLink': '',
                            'sourceLink': ''
                        }
                    }
                }
            ],
            'component2': {
                'uuid': component['uuid'],
                'text': 'component text 2 published',
                'link': {
                    'pk': str(self.primary_ltc.pk),
                    'slug': 'test-template-content',
                    'templateName': 'TestPage',
                    'title': 'component 2 link published title',
                    'url': '/test-url-2-pc/'
                },
                'image': {
                    'imageUrl': {
                        '1x': component_image.image_url(size=250),
                        '2x': component_image.image_url(size=500),
                        '4x': component_image.image_url(size=1000),
                    },
                    'licence': {
                        'licence': None,
                        'licenceVersion': '',
                        'creatorName': '',
                        'creatorLink': '',
                        'sourceLink': ''
                    }
                },
            },
            'image': {
                'imageUrl': {
                    '1x': content_image.image_url(size=250),
                    '2x': content_image.image_url(size=500),
                    '4x': content_image.image_url(size=1000),
                },
                'licence': {
                    'licence': None,
                    'licenceVersion': '',
                    'creatorName': '',
                    'creatorLink': '',
                    'sourceLink': ''
                }
            },
            'images': [
                {
                    'imageUrl': {
                        '1x': content_image_multiple.image_url(size=250),
                        '2x': content_image_multiple.image_url(size=500),
                        '4x': content_image_multiple.image_url(size=1000),
                    },
                    'licence': {
                        'licence': None,
                        'licenceVersion': '',
                        'creatorName': '',
                        'creatorLink': '',
                        'sourceLink': ''
                    }
                }
            ]
        }
        
        for key, value in expected_contents.items():
            self.assertEqual(expected_contents[key], contents[key])
        
        self.assertEqual(contents, expected_contents)
    
    
    @test_settings
    def test_published_deserialize(self):
        
        self.create_published_draft_contents()
        
        component_key = 'component2'
        component = self.primary_ltc.draft_contents[component_key]
        
        multi_component_key = 'component'
        multi_component = self.primary_ltc.draft_contents[multi_component_key][0]
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        self.primary_ltc.refresh_from_db()
        
        # fill it with draft contents
        self.primary_ltc.draft_title = self.template_content_title
        self.fill_localized_template_content() 
        
        context = {
            'preview' : False
        }
        
        serializer = LocalizedTemplateContentSerializer(self.primary_ltc, context=context)
        
        expected_data = {
            'title': 'Published title',
            'templateName': 'test-page',
            'templatePath': '/template_content/page/home/home.html',
            'version': 1,
            'contents': {
                'longText': 'published long test text which is a bit longer',
                'text': 'published short text',
                'link': {
                    'pk': str(self.primary_ltc.pk),
                    'slug': 'test-template-content',
                    'templateName': 'TestPage',
                    'title': 'published link title',
                    'url': '/test-url-published/'
                },
                'component': [
                    {
                        'uuid': multi_component['uuid'],
                        'text': 'component text published',
                        'link': {
                            'pk': str(self.primary_ltc.pk),
                            'slug': 'test-template-content',
                            'templateName': 'TestPage',
                            'title': 'component link title published',
                            'url': '/test-url-pc/'
                        },
                        'image': None
                    }
                ],
                'component2': {
                    'uuid': component['uuid'],
                    'text': 'component text 2 published',
                    'link': {
                        'pk': str(self.primary_ltc.pk),
                        'slug': 'test-template-content',
                        'templateName': 'TestPage',
                        'title': 'component 2 link published title',
                        'url': '/test-url-2-pc/'
                    },
                    'image': None
                },
                'image': None,
                'images': []
            },
            'linkedTaxa': [],
            'linkedTaxonProfiles': [],
        }
        
        self.assertEqual(serializer.data, expected_data)
        

class TestLocalizedNavigationSerializer(WithNavigation, WithUser, WithApp, TestCase):
    
    @test_settings
    def test_deserialize(self):
        
        context = {
            'preview' : True
        }
        serializer = LocalizedNavigationSerializer(self.localized_navigation, context=context)
        
        
        expected_data = {
            'navigation': [
                {
                    'linkName': 'nav entry 1 draft',
                    'link_name': 'nav entry 1 draft',
                    'url': None,
                    'children': []
                },
                {
                    'linkName': 'nav entry 2 draft',
                    'link_name': 'nav entry 2 draft',
                    'url': None,
                    'children': []
                }
            ]
        }
        
        self.assertEqual(serializer.data, expected_data)
        
        # published nav
        context = {
            'preview' : False
        }
        serializer_published = LocalizedNavigationSerializer(self.localized_navigation, context=context)
        
        
        expected_data_2 = {
            'navigation': [
                {
                    'linkName': 'nav entry 1',
                    'link_name': 'nav entry 1',
                    'url': None,
                    'children': []
                },
                {
                    'linkName': 'nav entry 2',
                    'link_name': 'nav entry 2',
                    'url': None,
                    'children': []
                }
            ]
        }
        
        self.assertEqual(serializer_published.data, expected_data_2)