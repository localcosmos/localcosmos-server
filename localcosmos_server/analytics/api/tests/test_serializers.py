from django.test import TestCase

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp

from localcosmos_server.analytics.api.serializers import AnonymousLogSerializer, EventCountSerializer
from localcosmos_server.analytics.tests.common import WithLogEntry

from localcosmos_server.analytics.api.views import EventCount

class TestAnonymousLogSerializer(WithLogEntry, WithApp, TestCase):

    def setUp(self):
        super().setUp()

        self.event_type = 'pageVisit'
        self.event_content = '/downloads'

    @test_settings
    def test_deserialize(self):
        
        data = {
            'app_version': self.app.published_version,
            'event_type': self.event_type,
            'event_content': self.event_content,
        }

        serializer = AnonymousLogSerializer(str(self.app.uuid), data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})


    @test_settings
    def test_serialize(self):
        
        log_entry = self.create_log_entry(self.app, self.event_type, self.event_content)

        serializer = AnonymousLogSerializer(str(self.app.uuid), log_entry)

        expected_output = {
            'id': log_entry.id,
            'app_version': None,
            'event_type': self.event_type,
            'event_content': self.event_content,
            'platform': None,
            'created_at': serializer.data['created_at'] # difficult formatting, do not test
        }

        for key, value in expected_output.items():
            self.assertEqual(value, serializer.data[key])

        self.assertEqual(serializer.data, expected_output)


    @test_settings
    def test_create(self):

        data = {
            'app_version': self.app.published_version,
            'event_type': self.event_type,
            'event_content': self.event_content,
        }

        serializer = AnonymousLogSerializer(str(self.app.uuid), data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        obj = serializer.create(serializer.validated_data)

        self.assertEqual(obj.app, self.app)



class TestEventCountSerializer(WithLogEntry, WithApp, TestCase):

    @test_settings
    def test_serialize(self):
        event_type = 'pageVisit'
        count = 10
        event_count = EventCount(event_type, count)

        serializer = EventCountSerializer(event_count)

        expected_data = {
            'event_type': event_type,
            'event_content': None,
            'count': count,
        }

        self.assertEqual(serializer.data, expected_data)

