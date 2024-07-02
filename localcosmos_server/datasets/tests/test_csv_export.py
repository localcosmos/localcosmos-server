from django.conf import settings
from django.test import TestCase

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithObservationForm

from localcosmos_server.tests.common import (test_settings, TEST_IMAGE_PATH, TEST_CLIENT_ID, TEST_PLATFORM,
    TEST_TIMESTAMP_OFFSET, TEST_LATITUDE, TEST_LONGITUDE, LARGE_TEST_IMAGE_PATH, DataCreator, TEST_TIMESTAMP,
    GEOJSON_POLYGON)

from localcosmos_server.datasets.csv_export import DatasetCSVExport

class TestDatasetCSVExport(WithMedia, WithObservationForm, WithApp, WithUser, TestCase):    
    
    @test_settings
    def test_init(self):
        
        exporter = DatasetCSVExport(self.app)
        
        self.assertTrue(exporter.csv_dir.startswith(settings.MEDIA_ROOT))
        self.assertTrue(exporter.filepath.startswith(settings.MEDIA_ROOT))
        
    
    @test_settings
    def test_get_queryset(self):
        
        observation_form = self.create_observation_form(
            observation_form_json=self.observation_form_point_json)
        
        dataset = self.create_dataset(observation_form=observation_form)
        
        dataset_image = self.create_dataset_image(dataset)
        
        exporter = DatasetCSVExport(self.app)
        
        qs = exporter.get_queryset()
        
        self.assertEqual(qs.count(), 1)
        
    
    @test_settings
    def test_write_csv(self):
        
        observation_form = self.create_observation_form(
            observation_form_json=self.observation_form_point_json)
        
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset)
        
        exporter = DatasetCSVExport(self.app)
        
        exporter.write_csv()