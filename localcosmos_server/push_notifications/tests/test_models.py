from django.test import TestCase
from django.db import IntegrityError

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser

from localcosmos_server.push_notifications.models import PushReceivingDevice, PushNotificationLog

from fcm_django.models import FCMDevice


@test_settings
class TestPushReceivingDevice(WithApp, TestCase):

    def setUp(self):
        super().setUp()
        self.fcm_device = FCMDevice.objects.create(
            registration_id='test-token', type='android', active=True
        )

    def test_save_defaults_language_code_to_primary_language(self):
        device = PushReceivingDevice(
            app=self.app, client_id='client-1', fcm_device=self.fcm_device
        )
        device.save()
        self.assertEqual(device.language_code, self.app.primary_language)

    def test_save_keeps_explicit_language_code(self):
        device = PushReceivingDevice(
            app=self.app, client_id='client-1', fcm_device=self.fcm_device, language_code='en'
        )
        device.save()
        self.assertEqual(device.language_code, 'en')

    def test_str(self):
        device = PushReceivingDevice.objects.create(
            app=self.app, client_id='client-1', fcm_device=self.fcm_device
        )
        self.assertIn(str(self.app), str(device))

    def test_unique_together_app_client_id(self):
        PushReceivingDevice.objects.create(
            app=self.app, client_id='client-1', fcm_device=self.fcm_device
        )
        fcm_device2 = FCMDevice.objects.create(registration_id='token-2', type='android', active=True)
        with self.assertRaises(IntegrityError):
            PushReceivingDevice.objects.create(
                app=self.app, client_id='client-1', fcm_device=fcm_device2
            )


@test_settings
class TestPushNotificationLog(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    def test_str(self):
        log = PushNotificationLog.objects.create(
            app=self.app,
            title='Test Title',
            recipients='5 device(s)',
            status=PushNotificationLog.STATUS_SUCCESS,
            sent_by=self.user,
        )
        self.assertIn('Test Title', str(log))
        self.assertIn('success', str(log))

    def test_default_status_is_success(self):
        log = PushNotificationLog.objects.create(app=self.app, sent_by=self.user)
        self.assertEqual(log.status, PushNotificationLog.STATUS_SUCCESS)

    def test_sent_by_nullable(self):
        log = PushNotificationLog.objects.create(app=self.app, sent_by=None)
        self.assertIsNone(log.sent_by)

    def test_ordering_latest_first(self):
        log1 = PushNotificationLog.objects.create(app=self.app, title='First', sent_by=self.user)
        log2 = PushNotificationLog.objects.create(app=self.app, title='Second', sent_by=self.user)
        logs = list(PushNotificationLog.objects.filter(app=self.app))
        self.assertEqual(logs[0].pk, log2.pk)
        self.assertEqual(logs[1].pk, log1.pk)
