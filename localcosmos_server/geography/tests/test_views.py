from django.contrib.gis.geos import Polygon, MultiPolygon
from django.test import TestCase
from django.urls import reverse

from localcosmos_server.geography.models import GeographyPolygon, PolygonCategory
from localcosmos_server.models import App
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser

import json


@test_settings
class TestGetPolygonCategories(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        self.ajax_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }

    def test_get_requires_ajax(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }

        response = self.client.get(reverse('geography:get_polygon_categories', kwargs=url_kwargs))
        self.assertEqual(response.status_code, 400)

    def test_get_context_data_filters_categories_by_app(self):
        PolygonCategory.objects.create(app=self.app, name='Biomes')
        PolygonCategory.objects.create(app=self.app, name='Protected areas')

        other_app = App.objects.create(
            name='Other app',
            uid='geography-view-tests-other-app',
            primary_language=self.app.primary_language,
            published_version_path=self.app.published_version_path,
        )
        PolygonCategory.objects.create(app=other_app, name='Foreign category')

        url_kwargs = {
            'app_uid': self.app.uid,
        }

        response = self.client.get(
            reverse('geography:get_polygon_categories', kwargs=url_kwargs),
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([category.name for category in response.context['categories']], ['Biomes', 'Protected areas'])


@test_settings
class TestManagePolygon(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        self.ajax_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }

        self.category = PolygonCategory.objects.create(
            app=self.app,
            name='Areas',
        )

        self.existing_polygon = GeographyPolygon.objects.create(
            app=self.app,
            category=self.category,
            name='Polygon one',
            code='P-1',
            geometry=self.get_geometry_3857(500000.0, 6000000.0),
        )

    def get_geometry_3857(self, x, y):
        polygon = Polygon(
            (
                (x, y),
                (x, y + 1000.0),
                (x + 1000.0, y + 1000.0),
                (x + 1000.0, y),
                (x, y),
            ),
            srid=3857,
        )
        return MultiPolygon(polygon, srid=3857)

    def get_geojson_payload(self, min_lon, min_lat):
        return json.dumps({
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {},
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [min_lon, min_lat],
                            [min_lon, min_lat + 0.01],
                            [min_lon + 0.01, min_lat + 0.01],
                            [min_lon + 0.01, min_lat],
                            [min_lon, min_lat],
                        ]],
                    },
                },
            ],
        })

    def test_get_requires_ajax(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'category_id': self.category.id,
            'polygon_id': self.existing_polygon.id,
        }

        response = self.client.get(reverse('geography:edit_polygon', kwargs=url_kwargs))
        self.assertEqual(response.status_code, 400)

    def test_get_edit_context_includes_4326_geometry(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'category_id': self.category.id,
            'polygon_id': self.existing_polygon.id,
        }

        response = self.client.get(reverse('geography:edit_polygon', kwargs=url_kwargs), **self.ajax_headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn('geojson_geometry_4326', response.context)

        ring = response.context['geojson_geometry_4326']['features'][0]['geometry']['coordinates'][0]
        for lon, lat in ring:
            self.assertLessEqual(abs(lon), 180)
            self.assertLessEqual(abs(lat), 90)

    def test_post_add_polygon(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'category_id': self.category.id,
        }

        payload = self.get_geojson_payload(11.0, 49.0)
        post_data = {
            'name': 'New polygon',
            'code': 'NEW-1',
            'polygon': payload,
        }

        response = self.client.post(reverse('geography:add_polygon', kwargs=url_kwargs), post_data, **self.ajax_headers)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        created = GeographyPolygon.objects.get(app=self.app, category=self.category, code='NEW-1')
        self.assertEqual(created.geometry.srid, 3857)

    def test_post_edit_polygon_consecutive_saves_return_fresh_geometry(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'category_id': self.category.id,
            'polygon_id': self.existing_polygon.id,
        }

        first_payload = self.get_geojson_payload(11.0, 49.0)
        second_payload = self.get_geojson_payload(12.0, 50.0)

        response_1 = self.client.post(
            reverse('geography:edit_polygon', kwargs=url_kwargs),
            {
                'name': 'Polygon one',
                'code': 'P-1',
                'polygon': first_payload,
            },
            **self.ajax_headers
        )
        self.assertEqual(response_1.status_code, 200)
        self.assertTrue(response_1.context['success'])

        response_2 = self.client.post(
            reverse('geography:edit_polygon', kwargs=url_kwargs),
            {
                'name': 'Polygon one',
                'code': 'P-1',
                'polygon': second_payload,
            },
            **self.ajax_headers
        )

        self.assertEqual(response_2.status_code, 200)
        self.assertTrue(response_2.context['success'])

        ring = response_2.context['geojson_geometry_4326']['features'][0]['geometry']['coordinates'][0]
        first_lon = ring[0][0]
        first_lat = ring[0][1]

        self.assertAlmostEqual(first_lon, 12.0, places=6)
        self.assertAlmostEqual(first_lat, 50.0, places=6)

        self.existing_polygon.refresh_from_db()
        self.assertEqual(self.existing_polygon.geometry.srid, 3857)
