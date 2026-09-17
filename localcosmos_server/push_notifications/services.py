from dataclasses import dataclass

from firebase_admin import messaging
from fcm_django.models import FCMDevice

from .models import PushReceivingDevice, PushNotificationLog


@dataclass
class NotificationPayload:
    title: str
    body: str
    data: dict | None = None


class PushNotificationService:

    _FCM_BATCH_SIZE = 500  # FCM multicast limit per request

    def __init__(self, app, user=None):
        self.app = app
        self.user = user
        self._translations = {}

    def send(self, title, body, language_code=None, data=None):
        receiving_devices = PushReceivingDevice.objects.filter(
            app=self.app,
            fcm_device__active=True,
        )
        if language_code:
            receiving_devices = receiving_devices.filter(language_code=language_code)

        fcm_devices = FCMDevice.objects.filter(push_receiving_device__in=receiving_devices)
        return [self._send_queryset(fcm_devices, title, body, language_code or '', data)]

    def add_translation(self, language_code, title, body, data=None):
        self._translations[language_code] = NotificationPayload(title=title, body=body, data=data)
        return self

    def send_translated(self):
        """Sends all translations added via add_translation(). Must include app.primary_language."""
        translations = self._translations
        if self.app.primary_language not in translations:
            raise ValueError(
                f"translations must include the app primary language '{self.app.primary_language}'"
            )

        covered_language_codes = list(translations.keys())
        self._translations = {}  # reset after send
        logs = []

        for language_code, payload in translations.items():
            receiving_devices = PushReceivingDevice.objects.filter(
                app=self.app,
                fcm_device__active=True,
                language_code=language_code,
            )
            fcm_devices = FCMDevice.objects.filter(push_receiving_device__in=receiving_devices)
            logs.append(self._send_queryset(
                fcm_devices, payload.title, payload.body, language_code, payload.data
            ))

        # send primary-language payload to devices with unrecognised language codes
        fallback = translations[self.app.primary_language]
        fallback_receiving = PushReceivingDevice.objects.filter(
            app=self.app,
            fcm_device__active=True,
        ).exclude(language_code__in=covered_language_codes)
        fallback_fcm = FCMDevice.objects.filter(push_receiving_device__in=fallback_receiving)

        if fallback_fcm.exists():
            logs.append(self._send_queryset(
                fallback_fcm, fallback.title, fallback.body, self.app.primary_language, fallback.data
            ))

        return logs

    def _send_queryset(self, fcm_devices, title, body, language_code, data):
        # FCM requires all data values to be strings
        str_data = {k: str(v) for k, v in data.items()} if data else {}

        tokens = list(fcm_devices.values_list('registration_id', flat=True))

        log = PushNotificationLog(
            app=self.app,
            title=title,
            body=body,
            data=data,
            language_code=language_code,
            recipients=f'{len(tokens)} device(s)',
            sent_by=self.user,
        )

        success_count = 0
        failure_count = 0
        errors = []

        try:
            for i in range(0, len(tokens), self._FCM_BATCH_SIZE):
                batch = tokens[i:i + self._FCM_BATCH_SIZE]
                message = messaging.MulticastMessage(
                    tokens=batch,
                    data=str_data,
                    notification=messaging.Notification(title=title, body=body),
                    android=messaging.AndroidConfig(priority='high'),
                    apns=messaging.APNSConfig(
                        headers={
                            'apns-priority': '10',
                            'apns-push-type': 'alert',
                        },
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                content_available=True,
                                mutable_content=True,
                            ),
                        ),
                    ),
                )
                result = messaging.send_each_for_multicast(message)
                unregistered_tokens = []
                for j, response in enumerate(result.responses):
                    if response.success:
                        success_count += 1
                    elif isinstance(response.exception, messaging.UnregisteredError):
                        unregistered_tokens.append(batch[j])
                    else:
                        failure_count += 1
                        errors.append(str(response.exception))
                if unregistered_tokens:
                    FCMDevice.objects.filter(registration_id__in=unregistered_tokens).update(active=False)

            if failure_count:
                log.status = PushNotificationLog.STATUS_FAILURE
                log.error_message = f'{failure_count} failure(s): {"; ".join(errors[:5])}'
            else:
                log.status = PushNotificationLog.STATUS_SUCCESS
        except Exception as exc:
            log.status = PushNotificationLog.STATUS_FAILURE
            log.error_message = str(exc)

        log.save()
        return log
