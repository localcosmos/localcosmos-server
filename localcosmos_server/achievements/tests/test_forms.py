from django.test import TestCase
from django.contrib.gis.geos import Polygon

from localcosmos_server.achievements.factor_types import FACTOR_DATASET_CREATED
from localcosmos_server.achievements.factor_types import FACTOR_GEOGRAPHY
from localcosmos_server.achievements.factor_types import FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER
from localcosmos_server.achievements.forms import DatasetConditionForm
from localcosmos_server.achievements.forms import GeographyConditionForm, PointRuleForm
from localcosmos_server.geography.models import GeographyPolygon, PolygonCategory
from localcosmos_server.achievements.models import PointRule
from localcosmos_server.models import App
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp


class TestPointRuleForm(WithApp, TestCase):

    @test_settings
    def test_valid_date_range(self):
        form = PointRuleForm(
            data={
                'name': 'First dataset',
                'points': 10,
                'awarded_for': 'First dataset bonus',
                'is_active': True,
                'match_mode': 'all',
                'valid_from': '2026-01-01 00:00:00',
                'valid_to': '2026-12-31 23:59:59',
                'input_language': self.app.primary_language,
            }
        )
        
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        self.assertTrue(is_valid)

    @test_settings
    def test_rejects_invalid_date_range(self):
        form = PointRuleForm(
            data={
                'name': 'First dataset',
                'points': 10,
                'awarded_for': 'First dataset bonus',
                'is_active': True,
                'match_mode': 'all',
                'valid_from': '2026-12-31 23:59:59',
                'valid_to': '2026-01-01 00:00:00',
                'input_language': self.app.primary_language,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('valid_to', form.errors)


class TestGeographyConditionForm(WithApp, TestCase):

    def setUp(self):
        super().setUp()
        self.category = PolygonCategory.objects.create(
            app=self.app,
            name='Test category',
        )

    @test_settings
    def test_geography_queryset_is_app_filtered(self):
        polygon = Polygon(
            ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)),
            srid=3857,
        )

        geography_in_app = GeographyPolygon.objects.create(
            app=self.app,
            category=self.category,
            geometry=polygon,
            name='In app',
        )

        other_app = App.objects.create(
            name='Other app',
            uid='test-other-app-for-geography-form',
            primary_language=self.app.primary_language,
            published_version_path=self.app.published_version_path,
        )

        other_category = PolygonCategory.objects.create(
            app=other_app,
            name='Other category',
        )

        GeographyPolygon.objects.create(
            app=other_app,
            category=other_category,
            geometry=polygon,
            name='Other app geography',
        )

        form = GeographyConditionForm(
            initial={
                'factor_type': FACTOR_GEOGRAPHY,
            },
            app=self.app,
        )

        self.assertEqual(list(form.fields['geography'].queryset), [geography_in_app])

    @test_settings
    def test_first_species_in_polygon_factor_rejects_geography_selection(self):
        polygon = Polygon(
            ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)),
            srid=3857,
        )

        geography = GeographyPolygon.objects.create(
            app=self.app,
            category=self.category,
            geometry=polygon,
            name='In app',
        )

        form = GeographyConditionForm(
            data={
                'factor_type': FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER,
                'geography': geography.pk,
            },
            app=self.app,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('geography', form.errors)


class TestDatasetConditionForm(WithApp, TestCase):

    @test_settings
    def test_dataset_created_factor_is_available(self):
        form = DatasetConditionForm()
        self.assertIn(
            (FACTOR_DATASET_CREATED, 'Dataset created'),
            form.fields['factor_type'].choices,
        )