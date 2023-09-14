from django.test import TestCase

from localcosmos_server.tests.mixins import WithApp, WithUser

from localcosmos_server.tests.common import test_settings
from localcosmos_server.mails import send_registration_confirmation_email

class TestRegistrationConfirmationEmail(WithUser, WithApp, TestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    @test_settings
    def test_send(self):
        send_registration_confirmation_email(self.user, self.app.uuid)