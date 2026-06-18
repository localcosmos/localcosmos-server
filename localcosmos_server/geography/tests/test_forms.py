from django.test import TestCase

from localcosmos_server.geography.forms import PolygonCategoryForm, PolygonForm
from localcosmos_server.geography.models import PolygonCategory
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp


@test_settings
class TestPolygonCategoryForm(WithApp, TestCase):

    @test_settings
    def test_form_fields(self):
        form = PolygonCategoryForm()

        self.assertIn('name', form.fields)
        self.assertNotEqual(form.fields['name'].help_text, '')

    @test_settings
    def test_valid_form_can_create_category(self):
        form = PolygonCategoryForm(
            data={
                'name': 'Protected areas',
            }
        )

        self.assertTrue(form.is_valid())

        category = form.save(commit=False)
        category.app = self.app
        category.save()

        db_category = PolygonCategory.objects.get(pk=category.pk)
        self.assertEqual(db_category.name, 'Protected areas')
        self.assertEqual(db_category.app, self.app)


@test_settings
class TestPolygonForm(TestCase):

    @test_settings
    def test_valid_geojson_string(self):
        form = PolygonForm(
            data={
                'polygon': '{"type":"FeatureCollection","features":[]}',
                'name': 'A polygon',
                'code': 'P-1',
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['polygon'], '{"type":"FeatureCollection","features":[]}')

    @test_settings
    def test_invalid_geometry_raises_validation_error(self):
        form = PolygonForm(
            data={
                'polygon': '{invalid json}',
                'name': 'A polygon',
                'code': 'P-1',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('polygon', form.errors)
        self.assertIn('Invalid geometry', form.errors['polygon'])

    @test_settings
    def test_missing_polygon_is_invalid(self):
        form = PolygonForm(
            data={
                'name': 'A polygon',
                'code': 'P-1',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('polygon', form.errors)
