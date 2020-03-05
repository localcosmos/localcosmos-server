from django.test import TestCase

from localcosmos_server.server_control_panel.forms import InstallAppForm, EditAppForm

from localcosmos_server.tests.mixins import WithPowerSetDic, WithImageForForm


class TestInstallAppForm(WithPowerSetDic, WithImageForForm, TestCase):


    def test_validation(self):
        zipfile = self.get_zipfile('test.zip')

        post_data = {
            'zipfile' : zipfile,
            'url' : 'http://localhost/',
        }

        file_keys = ['zipfile']

        required_fields = set(['zipfile', 'url'])

        self.validation_test(post_data, required_fields, InstallAppForm, file_keys=file_keys)
        

