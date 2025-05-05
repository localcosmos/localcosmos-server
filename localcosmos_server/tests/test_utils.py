from django.test import TestCase

from localcosmos_server.tests.common import test_settings
from localcosmos_server.utils import get_content_instance_app
from localcosmos_server.tests.mixins import (WithApp, WithUser, WithObservationForm, CommonSetUp,
                                             WithValidationRoutine)

from localcosmos_server.datasets.models import DatasetValidationRoutine
from localcosmos_server.template_content.tests.mixins import WithTemplateContent

class TestGetContentInstanceApp(WithTemplateContent, WithValidationRoutine, WithObservationForm,
                                CommonSetUp, WithApp, WithUser, TestCase):

    @test_settings
    def test_get_content_instance_app_for_validation_routine(self):
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)
        
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        
        app = get_content_instance_app(validation_routine)
        self.assertEqual(app, self.app)
        
    @test_settings
    def test_get_content_instance_app_for_dataset(self):
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)
        
        app = get_content_instance_app(dataset)
        self.assertEqual(app, self.app)
        
    @test_settings
    def test_get_content_instance_app_for_template_content(self):
        
        app = get_content_instance_app(self.template_content)
        self.assertEqual(app, self.app)