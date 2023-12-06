from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser
from localcosmos_server.datasets.api.tests.test_views import CreatedUsersMixin
from localcosmos_server.analytics.tests.common import WithLogEntry

from localcosmos_server.analytics.models import AnonymousLog

import json

class TestCreateAnonymousLogEntry(WithUser, WithApp, CreatedUsersMixin, APITestCase):

    event_type = 'pageVisit'
    event_content = '/testView'

    @test_settings
    def test_post_minimal(self):

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_create_anonymous_log_entry', kwargs=url_kwargs)

        post_data = {
            'eventType': self.event_type,
            'eventContent': self.event_content,
        }

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        qry = AnonymousLog.objects.filter(event_type=self.event_type, event_content=self.event_content)
        self.assertTrue(qry.exists())

    
    @test_settings
    def test_post_full(self):
        
        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_create_anonymous_log_entry', kwargs=url_kwargs)

        post_data = {
            'eventType': self.event_type,
            'eventContent': self.event_content,
            'appVersion': '1.0',
            'platform': 'browser',
        }

        response = self.client.post(url, post_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        qry = AnonymousLog.objects.filter(event_type=self.event_type, event_content=self.event_content)
        self.assertTrue(qry.exists())

        obj = qry.last()

        self.assertEqual(obj.app, self.app)
        self.assertEqual(obj.event_type, self.event_type)
        self.assertEqual(obj.event_content, self.event_content)
        self.assertEqual(obj.app_version, post_data['appVersion'])
        self.assertEqual(obj.platform, post_data['platform'])


class TestGetEventCount(WithLogEntry, WithUser, WithApp, CreatedUsersMixin, APITestCase):

    event_type = 'pageVisit'
    event_content = '/testView'

    @test_settings
    def test_get(self):

        url_kwargs = {
            'app_uuid' : self.app.uuid,
        }

        url = reverse('api_get_anonymous_log_event_count', kwargs=url_kwargs)

        url_parameters = {
            'event-type': self.event_type
        }
        response = self.client.get(url, url_parameters)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_content = {
            'eventType': self.event_type,
            'count': 0,
            'eventContent': None,
        }

        self.assertEqual(json.loads(response.content), expected_content)

        log_entry = self.create_log_entry(self.app, self.event_type, self.event_content)
        log_entry_2 = self.create_log_entry(self.app, self.event_type, '/download')

        response = self.client.get(url, url_parameters)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_content = {
            'eventType': self.event_type,
            'count': 2,
            'eventContent': None,
        }

        self.assertEqual(json.loads(response.content), expected_content)

        # filter also by event content
        url_parameters = {
            'event-type': self.event_type,
            'event-content': self.event_content,
        }
        response = self.client.get(url, url_parameters)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_content = {
            'eventType': self.event_type,
            'count': 1,
            'eventContent': self.event_content,
        }

        self.assertEqual(json.loads(response.content), expected_content)