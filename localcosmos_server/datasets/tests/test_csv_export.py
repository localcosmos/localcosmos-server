from django.conf import settings
from django.test import TestCase
from django.test import RequestFactory
from django.urls import reverse

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithObservationForm

from localcosmos_server.tests.common import (test_settings, TEST_IMAGE_PATH, TEST_CLIENT_ID, TEST_PLATFORM,
    TEST_TIMESTAMP_OFFSET, TEST_LATITUDE, TEST_LONGITUDE, LARGE_TEST_IMAGE_PATH, DataCreator, TEST_TIMESTAMP,
    GEOJSON_POLYGON)

from localcosmos_server.datasets.csv_export import DatasetCSVExport

class TestDatasetCSVExport(WithMedia, WithObservationForm, WithApp, WithUser, TestCase):
    
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        
    def get_request(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }
        url = reverse('datasets:create_download_datasets_csv', kwargs=url_kwargs)
        request = self.factory.get(url)
        return request

    
    @test_settings
    def test_init(self):
        
        request = self.get_request()
        exporter = DatasetCSVExport(request, self.app)
        
        self.assertTrue(exporter.csv_dir.startswith(settings.MEDIA_ROOT))
        self.assertTrue(exporter.filepath.startswith(settings.MEDIA_ROOT))
        
    
    @test_settings
    def test_get_queryset(self):
        
        observation_form = self.create_observation_form(
            observation_form_json=self.observation_form_point_json)
        
        dataset = self.create_dataset(observation_form=observation_form)
        
        dataset_image = self.create_dataset_image(dataset)
        
        request = self.get_request()
        exporter = DatasetCSVExport(request, self.app)
        
        qs = exporter.get_queryset()
        
        self.assertEqual(qs.count(), 1)
        
    
    @test_settings
    def test_write_csv(self):
        
        observation_form = self.create_observation_form(
            observation_form_json=self.observation_form_point_json)
        
        dataset = self.create_dataset(observation_form=observation_form)
        dataset_image = self.create_dataset_image(dataset)
        
        request = self.get_request()
        exporter = DatasetCSVExport(request, self.app)
        
        exporter.write_csv()