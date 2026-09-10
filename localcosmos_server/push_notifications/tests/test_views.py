from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser

from localcosmos_server.push_notifications.models import PushNotificationLog


AJAX_HEADER = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


class PushNotificationViewTestBase(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()

    def get_url(self, name):
        return reverse(f'push_notifications:{name}', kwargs={'app_uid': self.app.uid})


@test_settings
class TestManagePushNotifications(PushNotificationViewTestBase):

    def test_get_logged_out_redirects(self):
        url = self.get_url('manage_push_notifications')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('log_in'), response.url)

    def test_get_permission_denied_for_user_without_role(self):
        self.client.login(username=self.test_username, password=self.test_password)
        url = self.get_url('manage_push_notifications')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in_as_superuser(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('manage_push_notifications')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_context_contains_required_keys(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('manage_push_notifications')
        response = self.client.get(url)
        self.assertIn('push_notification_logs', response.context)
        self.assertIn('devices_per_language', response.context)
        self.assertIn('form', response.context)

    def test_get_devices_per_language_covers_all_app_languages(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('manage_push_notifications')
        response = self.client.get(url)
        languages_in_context = [lang for lang, _ in response.context['devices_per_language']]
        for lang in self.app.languages():
            self.assertIn(lang, languages_in_context)


@test_settings
class TestSendPushNotification(PushNotificationViewTestBase):

    def get_valid_post_data(self, language_code=''):
        return {'title': 'Hello', 'body': 'World', 'language_code': language_code}

    def test_get_logged_out_redirects(self):
        url = self.get_url('send_push_notification')
        response = self.client.get(url, **AJAX_HEADER)
        self.assertEqual(response.status_code, 302)

    def test_get_without_ajax_header_returns_400(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('send_push_notification')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_get_logged_in_with_ajax_header(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('send_push_notification')
        response = self.client.get(url, **AJAX_HEADER)
        self.assertEqual(response.status_code, 200)

    @patch('localcosmos_server.push_notifications.views.PushNotificationService')
    def test_post_to_all_languages_calls_send_translated(self, MockService):
        MockService.return_value.send_translated.return_value = []
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('send_push_notification')
        response = self.client.post(url, self.get_valid_post_data(), **AJAX_HEADER)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        self.assertFalse(response.context['fcm_has_failures'])
        MockService.assert_called_once_with(self.app, user=self.superuser)
        MockService.return_value.send_translated.assert_called_once()

    @patch('localcosmos_server.push_notifications.views.PushNotificationService')
    def test_post_to_specific_language_calls_send(self, MockService):
        MockService.return_value.send.return_value = []
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('send_push_notification')
        response = self.client.post(url, self.get_valid_post_data(language_code='de'), **AJAX_HEADER)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        self.assertFalse(response.context['fcm_has_failures'])
        MockService.assert_called_once_with(self.app, user=self.superuser)
        MockService.return_value.send.assert_called_once_with('Hello', 'World', language_code='de')

    @patch('localcosmos_server.push_notifications.views.PushNotificationService')
    def test_post_fcm_failure_sets_has_failures(self, MockService):
        failed_log = PushNotificationLog(
            status=PushNotificationLog.STATUS_FAILURE,
            error_message='token not registered',
            language_code='de',
        )
        MockService.return_value.send.return_value = [failed_log]
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('send_push_notification')
        response = self.client.post(url, self.get_valid_post_data(language_code='de'), **AJAX_HEADER)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        self.assertTrue(response.context['fcm_has_failures'])
        self.assertContains(response, 'token not registered')


@test_settings
class TestGetNotificationLogs(PushNotificationViewTestBase):

    def test_get_logged_out_redirects(self):
        url = self.get_url('get_notification_logs')
        response = self.client.get(url, **AJAX_HEADER)
        self.assertEqual(response.status_code, 302)

    def test_get_without_ajax_header_returns_400(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('get_notification_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_get_logged_in_with_ajax_header(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('get_notification_logs')
        response = self.client.get(url, **AJAX_HEADER)
        self.assertEqual(response.status_code, 200)

    def test_get_context_contains_logs_for_app(self):
        PushNotificationLog.objects.create(app=self.app, title='Test', sent_by=self.superuser)
        self.client.login(username=self.test_superuser_username, password=self.test_password)
        url = self.get_url('get_notification_logs')
        response = self.client.get(url, **AJAX_HEADER)
        self.assertIn('push_notification_logs', response.context)
        self.assertEqual(response.context['push_notification_logs'].count(), 1)
