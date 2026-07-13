from rest_framework.test import APITestCase
from rest_framework import status

from localcosmos_server.datasets.api.tests.test_views import CreatedUsersMixin

from localcosmos_server.template_content.tests.mixins import WithTemplateContent, WithNavigation, _collect_nested_differences

from localcosmos_server.tests.common import (test_settings,)
from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithServerContentImage

from django.urls import reverse

import json, difflib

class TestGetTemplateContentPreview(WithTemplateContent, WithServerContentImage, WithMedia, CreatedUsersMixin,
                                    WithApp, WithUser, APITestCase):
    
    
    def setUp(self):
        super().setUp()
        self.fill_localized_template_content()
        
        
    def assert_serializer_data_equal(self, serializer_data, expected_data):
        differences = _collect_nested_differences(expected_data, serializer_data)
        if not differences:
            return

        expected_json = json.dumps(expected_data, indent=2, sort_keys=True, ensure_ascii=False)
        actual_json = json.dumps(serializer_data, indent=2, sort_keys=True, ensure_ascii=False)

        unified_diff = '\n'.join(
            difflib.unified_diff(
                expected_json.splitlines(),
                actual_json.splitlines(),
                fromfile='expected_data',
                tofile='serializer.data',
                lineterm='',
            )
        )

        difference_lines = '\n'.join(f"- {difference}" for difference in differences)
        self.fail(f"Serializer data mismatch:\n{difference_lines}\n\nUnified diff:\n{unified_diff}")
        
        
    @test_settings
    def test_get(self):
        
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'slug': self.primary_ltc.slug,
        }

        url = reverse('get_template_content_preview', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        component_key = 'component2'
        component = self.primary_ltc.draft_contents[component_key]

        multi_component_key = 'component'
        multi_component = self.primary_ltc.draft_contents[multi_component_key][0]

        stream_item_key = 'stream'
        stream_item = self.primary_ltc.draft_contents[stream_item_key][0]
        
        expected_response = {
            'title' : 'Test template content',
            'templateName' : 'test-page',
            'version' : 1,
            'contents' : {
                'link' : {
                    'pk' : str(self.primary_ltc.pk),
                    'url' : '/pages/TestPage/test-template-content/',
                    'slug' : 'test-template-content',
                    'title' : 'Test template content',
                    'templateName' : 'TestPage',
                    'author': None,
                },
                'text' : 'short text',
                "stream":[
                    {
                        "link":{
                            "pk": stream_item['link']['pk'],
                            "url": '/pages/TestPage/test-template-content/',
                            "slug": stream_item['link']['slug'],
                            "title": 'Test template content',
                            "templateName": stream_item['link']['templateName'],
                            "author": None,
                        },
                        "text": stream_item['text'],
                        "uuid": stream_item['uuid'],
                        "templateName": stream_item['templateName'],
                        "image": None
                    }
                ],
                'longText' : 'test text which is a bit longer',
                'component' : [
                    {
                        'link' : {
                            'pk' : str(self.primary_ltc.pk),
                            'url' : '/pages/TestPage/test-template-content/',
                            'slug' : 'test-template-content',
                            'title' : 'Test template content',
                            'templateName' : 'TestPage',
                            'author': None,
                        },
                        'text' : 'component text',
                        'uuid' : multi_component['uuid'],
                        'image' : None
                    }
                ],
                'component2' : {
                    'link' : {
                        'pk' : str(self.primary_ltc.pk),
                        'url' : '/pages/TestPage/test-template-content/',
                        'slug' : 'test-template-content',
                        'title' : 'Test template content',
                        'templateName' : 'TestPage',
                        'author': None,
                    },
                    'text' : 'component text 2',
                    'uuid' : component['uuid'],
                    'image' : None
                },
                'image' : None,
                'images' : []
            },
            'linkedTaxa':[],
            'linkedTaxonProfiles':[],
            'publishedAt':None,
            'createdAt': self.primary_ltc.created_at.isoformat(),
            'lastModified': self.primary_ltc.last_modified.isoformat(),
            'uuid': str(self.primary_ltc.template_content.uuid),
            'language': self.primary_ltc.language,
            'slug': 'test-template-content',
            'author': None
        }
        
        

        self.assert_serializer_data_equal(json.loads(response.content), expected_response)


class TestGetTemplateContent(WithTemplateContent, WithServerContentImage, WithMedia, CreatedUsersMixin,
                                    WithApp, WithUser, APITestCase):
    
    def setUp(self):
        super().setUp()
        self.fill_localized_template_content()
        
    
    @test_settings
    def test_get(self):
        
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'slug': self.primary_ltc.slug,
        }

        url = reverse('get_template_content', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

  
class TestGetNavigation(CreatedUsersMixin, WithNavigation, WithApp, WithUser, APITestCase):
    
    @test_settings
    def test_get(self):
        
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'navigation_type': 'main',
            'language': self.app.primary_language,
        }
        
        url = reverse('get_template_content_navigation', kwargs=url_kwargs)
        
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        content = json.loads(response.content)
        
        expected_content = {
            'navigation': [
                {
                    'url': None,
                    'children': [],
                    'linkName': 'nav entry 1'
                },
                {
                    'url': None,
                    'children': [],
                    'linkName': 'nav entry 2'
                }
            ]
        }
        
        self.assertEqual(content, expected_content)
        
        
    @test_settings
    def test_get_404(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'navigation_type': 'something',
            'language': self.app.primary_language,
        }
        
        url = reverse('get_template_content_navigation', kwargs=url_kwargs)
        
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    
class TestGetNavigationPreview(CreatedUsersMixin, WithNavigation, WithApp, WithUser, APITestCase):
    
    @test_settings
    def test_get(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'navigation_type': 'main',
            'language': self.app.primary_language,
        }
        
        url = reverse('get_template_content_navigation_preview', kwargs=url_kwargs)
        
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        content = json.loads(response.content)
        
        expected_content = {
            'navigation': [
                {
                    'url': None,
                    'children': [],
                    'linkName': 'nav entry 1 draft'
                },
                {
                    'url': None,
                    'children': [],
                    'linkName': 'nav entry 2 draft'
                }
            ]
        }
        
        self.assertEqual(content, expected_content)
    
    @test_settings
    def test_get_404(self):
        url_kwargs = {
            'app_uuid': str(self.app.uuid),
            'navigation_type': 'something',
            'language': self.app.primary_language,
        }
        
        url = reverse('get_template_content_navigation_preview', kwargs=url_kwargs)
        
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)