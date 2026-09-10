from django.test import TestCase

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp

from localcosmos_server.push_notifications.forms import SendPushNotificationForm


@test_settings
class TestSendPushNotificationForm(WithApp, TestCase):

    def setUp(self):
        super().setUp()

    def get_valid_data(self):
        return {
            'title': 'Hello',
            'body': 'World',
            'language_code': '',
        }

    def test_valid_form_all_languages(self):
        form = SendPushNotificationForm(self.app, data=self.get_valid_data())
        self.assertTrue(form.is_valid())

    def test_valid_form_specific_language(self):
        data = self.get_valid_data()
        data['language_code'] = 'de'
        form = SendPushNotificationForm(self.app, data=data)
        self.assertTrue(form.is_valid())

    def test_title_required(self):
        data = self.get_valid_data()
        del data['title']
        form = SendPushNotificationForm(self.app, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_body_required(self):
        data = self.get_valid_data()
        del data['body']
        form = SendPushNotificationForm(self.app, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('body', form.errors)

    def test_language_code_not_required(self):
        data = self.get_valid_data()
        data['language_code'] = ''
        form = SendPushNotificationForm(self.app, data=data)
        self.assertTrue(form.is_valid())

    def test_language_code_choices_include_app_languages(self):
        form = SendPushNotificationForm(self.app)
        choices = dict(form.fields['language_code'].choices)
        self.assertIn('', choices)
        for lang in self.app.languages():
            self.assertIn(lang, choices)

    def test_data_field_is_optional(self):
        data = self.get_valid_data()
        form = SendPushNotificationForm(self.app, data=data)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['data'])

    def test_data_field_parses_valid_json(self):
        data = self.get_valid_data()
        data['data'] = '{"link": "/content/123/"}'
        form = SendPushNotificationForm(self.app, data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['data'], {'link': '/content/123/'})

    def test_data_field_rejects_invalid_json(self):
        data = self.get_valid_data()
        data['data'] = 'not-json'
        form = SendPushNotificationForm(self.app, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('data', form.errors)
