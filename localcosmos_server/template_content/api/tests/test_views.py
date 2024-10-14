from rest_framework.test import APITestCase
from rest_framework import status

from localcosmos_server.datasets.api.tests.test_views import CreatedUsersMixin

from localcosmos_server.template_content.tests.mixins import WithTemplateContent

from localcosmos_server.tests.common import (test_settings,)
from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithServerContentImage

from django.urls import reverse

import json

class TestGetTemplateContentPreview(WithTemplateContent, WithServerContentImage, WithMedia, CreatedUsersMixin,
                                    WithApp, WithUser, APITestCase):
    
    
    def setUp(self):
        super().setUp()
        self.fill_localized_template_content()
        
        
    @test_settings
    def test_get(self):
        
        url_kwargs = {
            'slug': self.primary_ltc.slug,
        }

        url = reverse('get_template_content_preview', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        component_key = 'component2'
        component = self.primary_ltc.draft_contents[component_key]

        multi_component_key = 'component'
        multi_component = self.primary_ltc.draft_contents[multi_component_key][0]
        
        expected_response = {
            'title' : 'Test template content',
            'templateName' : 'test-page',
            'templatePath' : '/template_content/page/home/home.html',
            'version' : 1,
            'contents' : {
                'link' : {
                    'pk' : str(self.primary_ltc.pk),
                    'url' : '/test-url/',
                    'slug' : 'test-template-content',
                    'title' : 'link title',
                    'templateName' : 'TestPage'
                },
                'text' : 'short text',
                'longText' : 'test text which is a bit longer',
                'component' : [
                    {
                        'link' : {
                            'pk' : str(self.primary_ltc.pk),
                            'url' : '/test-url/',
                            'slug' : 'test-template-content',
                            'title' : 'component link title',
                            'templateName' : 'TestPage'
                        },
                        'text' : 'component text',
                        'uuid' : multi_component['uuid'],
                        'image' : None
                    }
                ],
                'component2' : {
                    'link' : {
                        'pk' : str(self.primary_ltc.pk),
                        'url' : '/test-url-2/',
                        'slug' : 'test-template-content',
                        'title' : 'component 2 link title',
                        'templateName' : 'TestPage'
                    },
                    'text' : 'component text 2',
                    'uuid' : component['uuid'],
                    'image' : None
                },
                'image' : None,
                'images' : []
                }
        }

        self.assertEqual(json.loads(response.content), expected_response)


class TestGetTemplateContent(WithTemplateContent, WithServerContentImage, WithMedia, CreatedUsersMixin,
                                    WithApp, WithUser, APITestCase):
    
    def setUp(self):
        super().setUp()
        self.fill_localized_template_content()
        
    
    @test_settings
    def test_get(self):
        
        url_kwargs = {
            'slug': self.primary_ltc.slug,
        }

        url = reverse('get_template_content', kwargs=url_kwargs)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        self.primary_ltc.template_content.publish(language=self.primary_ltc.language)
        
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)