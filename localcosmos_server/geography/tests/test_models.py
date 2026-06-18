from django.test import TestCase
from django.contrib.gis.geos import Polygon, MultiPolygon

from localcosmos_server.geography.models import GeographyPolygon, PolygonCategory
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp


@test_settings
class TestPolygonCategory(WithApp, TestCase):

	def test_polygons_property_filters_and_orders(self):
		category = PolygonCategory.objects.create(
			app=self.app,
			name='Areas',
		)

		other_category = PolygonCategory.objects.create(
			app=self.app,
			name='Other',
		)

		polygon = Polygon(
			(
				(0.0, 0.0),
				(0.0, 1000.0),
				(1000.0, 1000.0),
				(1000.0, 0.0),
				(0.0, 0.0),
			),
			srid=3857,
		)
		multipolygon = MultiPolygon(polygon, srid=3857)

		polygon_c = GeographyPolygon.objects.create(
			app=self.app,
			category=category,
			name='C area',
			geometry=multipolygon,
		)
		polygon_a = GeographyPolygon.objects.create(
			app=self.app,
			category=category,
			name='A area',
			geometry=multipolygon,
		)

		GeographyPolygon.objects.create(
			app=self.app,
			category=other_category,
			name='Should be filtered out',
			geometry=multipolygon,
		)

		self.assertEqual(list(category.polygons), [polygon_a, polygon_c])

	def test_str(self):
		category = PolygonCategory.objects.create(
			app=self.app,
			name='Protected areas',
		)

		self.assertEqual(str(category), 'Protected areas')


@test_settings
class TestGeographyPolygon(WithApp, TestCase):

	def setUp(self):
		super().setUp()

		self.category = PolygonCategory.objects.create(
			app=self.app,
			name='Test category',
		)

		polygon = Polygon(
			(
				(0.0, 0.0),
				(0.0, 1000.0),
				(1000.0, 1000.0),
				(1000.0, 0.0),
				(0.0, 0.0),
			),
			srid=3857,
		)

		self.geometry = MultiPolygon(polygon, srid=3857)

	def test_geometry_field_srid(self):
		field = GeographyPolygon._meta.get_field('geometry')
		self.assertEqual(field.srid, 3857)

	def test_str_prefers_name(self):
		geography_polygon = GeographyPolygon.objects.create(
			app=self.app,
			category=self.category,
			name='Named polygon',
			code='CODE-1',
			geometry=self.geometry,
		)

		self.assertEqual(str(geography_polygon), 'Named polygon (Test category)')

	def test_str_falls_back_to_code(self):
		geography_polygon = GeographyPolygon.objects.create(
			app=self.app,
			category=self.category,
			name=None,
			code='CODE-2',
			geometry=self.geometry,
		)

		self.assertEqual(str(geography_polygon), 'CODE-2 (Test category)')

	def test_str_falls_back_to_pk(self):
		geography_polygon = GeographyPolygon.objects.create(
			app=self.app,
			category=self.category,
			name=None,
			code=None,
			geometry=self.geometry,
		)

		self.assertEqual(str(geography_polygon), '{0} (Test category)'.format(geography_polygon.pk))
