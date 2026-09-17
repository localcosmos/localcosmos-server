from django.test import TestCase
from unittest.mock import patch, MagicMock

from firebase_admin import messaging as fbm

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser

from localcosmos_server.push_notifications.models import PushReceivingDevice, PushNotificationLog
from localcosmos_server.push_notifications.services import PushNotificationService

from fcm_django.models import FCMDevice


def make_receiving_device(app, registration_id, client_id, language_code='de'):
    fcm = FCMDevice.objects.create(registration_id=registration_id, type='android', active=True)
    return PushReceivingDevice.objects.create(
        app=app, client_id=client_id, fcm_device=fcm, language_code=language_code
    )


def mock_batch_response(success_count=1, failure_count=0, failed_exceptions=None):
    r = MagicMock()
    r.success_count = success_count
    r.failure_count = failure_count
    responses = []
    for exc in (failed_exceptions or []):
        m = MagicMock()
        m.success = False
        m.exception = exc
        responses.append(m)
    for _ in range(success_count):
        m = MagicMock()
        m.success = True
        responses.append(m)
    r.responses = responses
    return r


@test_settings
class TestPushNotificationServiceSend(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.device = make_receiving_device(self.app, 'token-1', 'client-1', 'de')
        self.service = PushNotificationService(self.app, user=self.user)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_creates_success_log(self, mock_send):
        mock_send.return_value = mock_batch_response()
        (log,) = self.service.send('Hello', 'World')
        self.assertEqual(log.status, PushNotificationLog.STATUS_SUCCESS)
        self.assertEqual(log.app, self.app)
        self.assertEqual(log.title, 'Hello')
        self.assertEqual(log.body, 'World')
        self.assertEqual(log.sent_by, self.user)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_creates_failure_log_on_fcm_failure(self, mock_send):
        exc = Exception('token not registered')
        mock_send.return_value = mock_batch_response(success_count=0, failure_count=1, failed_exceptions=[exc])
        (log,) = self.service.send('Hello', 'World')
        self.assertEqual(log.status, PushNotificationLog.STATUS_FAILURE)
        self.assertIn('1 failure(s)', log.error_message)
        self.assertIn('token not registered', log.error_message)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_unregistered_device_does_not_fail_log(self, mock_send):
        unregistered_exc = MagicMock(spec=fbm.UnregisteredError)
        mock_send.return_value = mock_batch_response(
            success_count=0, failure_count=1, failed_exceptions=[unregistered_exc]
        )
        (log,) = self.service.send('Hello', 'World')
        self.assertEqual(log.status, PushNotificationLog.STATUS_SUCCESS)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_unregistered_device_deactivates_fcm_device(self, mock_send):
        unregistered_exc = MagicMock(spec=fbm.UnregisteredError)
        mock_send.return_value = mock_batch_response(
            success_count=0, failure_count=1, failed_exceptions=[unregistered_exc]
        )
        self.service.send('Hello', 'World')
        self.device.fcm_device.refresh_from_db()
        self.assertFalse(self.device.fcm_device.active)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_creates_failure_log_on_exception(self, mock_send):
        mock_send.side_effect = Exception('network error')
        (log,) = self.service.send('Hello', 'World')
        self.assertEqual(log.status, PushNotificationLog.STATUS_FAILURE)
        self.assertIn('network error', log.error_message)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_filters_by_language_code(self, mock_send):
        mock_send.return_value = mock_batch_response()
        make_receiving_device(self.app, 'token-en', 'client-en', 'en')
        (log,) = self.service.send('Hi', 'There', language_code='en')
        self.assertEqual(log.language_code, 'en')
        self.assertIn('1', log.recipients)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_excludes_inactive_devices(self, mock_send):
        mock_send.return_value = mock_batch_response()
        inactive_fcm = FCMDevice.objects.create(
            registration_id='inactive-token', type='android', active=False
        )
        PushReceivingDevice.objects.create(
            app=self.app, client_id='inactive-client', fcm_device=inactive_fcm, language_code='de'
        )
        (log,) = self.service.send('Hi', 'There')
        self.assertIn('1', log.recipients)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_converts_data_values_to_strings(self, mock_send):
        mock_send.return_value = mock_batch_response()
        self.service.send('Hi', 'There', data={'count': 5, 'flag': True})
        message = mock_send.call_args[0][0]
        self.assertEqual(message.data, {'count': '5', 'flag': 'True'})

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_records_recipient_count(self, mock_send):
        mock_send.return_value = mock_batch_response()
        make_receiving_device(self.app, 'token-2', 'client-2', 'de')
        (log,) = self.service.send('Hi', 'There')
        self.assertIn('2', log.recipients)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_batches_large_token_list(self, mock_send):
        mock_send.return_value = mock_batch_response()
        make_receiving_device(self.app, 'token-2', 'client-2', 'de')
        make_receiving_device(self.app, 'token-3', 'client-3', 'de')
        PushNotificationService._FCM_BATCH_SIZE = 2
        try:
            self.service.send('Hi', 'There')
        finally:
            PushNotificationService._FCM_BATCH_SIZE = 500
        self.assertEqual(mock_send.call_count, 2)


@test_settings
class TestPushNotificationServiceSendTranslated(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        make_receiving_device(self.app, 'token-de', 'client-de', 'de')
        make_receiving_device(self.app, 'token-en', 'client-en', 'en')
        self.service = PushNotificationService(self.app, user=self.user)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_translated_sends_per_language(self, mock_send):
        mock_send.return_value = mock_batch_response()
        self.service.add_translation('de', 'Hallo', 'Welt')
        self.service.add_translation('en', 'Hello', 'World')
        logs = self.service.send_translated()
        self.assertEqual(len(logs), 2)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_translated_requires_primary_language(self, mock_send):
        mock_send.return_value = mock_batch_response()
        self.service.add_translation('en', 'Hello', 'World')
        with self.assertRaises(ValueError):
            self.service.send_translated()

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_translated_resets_translations_after_send(self, mock_send):
        mock_send.return_value = mock_batch_response()
        self.service.add_translation('de', 'Hallo', 'Welt')
        self.service.add_translation('en', 'Hello', 'World')
        self.service.send_translated()
        self.assertEqual(self.service._translations, {})

    @patch('firebase_admin.messaging.send_each_for_multicast')
    def test_send_translated_fallback_for_unknown_language(self, mock_send):
        mock_send.return_value = mock_batch_response()
        make_receiving_device(self.app, 'token-fr', 'client-fr', 'fr')
        self.service.add_translation('de', 'Hallo', 'Welt')
        self.service.add_translation('en', 'Hello', 'World')
        logs = self.service.send_translated()
        # de + en + fallback for the 'fr' device
        self.assertEqual(len(logs), 3)

    def test_add_translation_returns_self_for_chaining(self):
        result = self.service.add_translation('de', 'Hallo', 'Welt')
        self.assertIs(result, self.service)
