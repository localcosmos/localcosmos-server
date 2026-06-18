from django.test import TestCase

from localcosmos_server.achievements.factor_types import FACTOR_DATASET_CREATED
from localcosmos_server.achievements.factor_types import FACTOR_IS_FIRST_DATASET_FOR_USER
from localcosmos_server.achievements.factor_types import FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER
from localcosmos_server.achievements.models import PointRule, PointRuleCondition, UserPoints
from localcosmos_server.achievements.point_calculators.DatasetPointsAwarder import DatasetPointsAwarder
from localcosmos_server.geography.models import GeographyPolygon, PolygonCategory
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithObservationForm, WithUser

from localcosmos_server.taxonomy.lazy import LazyAppTaxon

class WithPolygon:
    def setUp(self):
        super().setUp()
        self.polygon_category = PolygonCategory.objects.create(
            app=self.app,
            name='Awarder polygons',
        )

    def create_polygon_for_dataset(self, dataset, name='Polygon B'):
        point = dataset.coordinates.clone()
        if point.srid != 3857:
            point.transform(3857)

        polygon = point.buffer(1000)
        polygon.srid = 3857

        return GeographyPolygon.objects.create(
            app=self.app,
            category=self.polygon_category,
            name=name,
            geometry=polygon,
        )

class WithLazyTaxon:
    
    def setUp(self):
        super().setUp()
    
        test_taxon_kwargs = {
            "taxon_source": "taxonomy.sources.col",
            "name_uuid": "eb53f49f-1f80-4505-9d56-74216ac4e548",
            "taxon_nuid": "006002009001005001001",
            "taxon_latname": "Abies alba",
            "taxon_author" : "Linnaeus",
            "gbif_nubKey": 2685484,
        }
        self.lazy_taxon = LazyAppTaxon(**test_taxon_kwargs)


class TestDatasetPointsAwarder(WithPolygon, WithLazyTaxon, WithObservationForm, WithApp, WithUser, TestCase):

    @test_settings
    def test_awards_points_for_first_user_dataset_condition(self):
        user = self.create_user()
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form, user=user)

        rule = PointRule.objects.create(
            app=self.app,
            name='First dataset',
            points=10,
            awarded_for='First dataset bonus',
        )
        PointRuleCondition.objects.create(
            rule=rule,
            factor_type=FACTOR_IS_FIRST_DATASET_FOR_USER,
            operator='equals',
            value_json=True,
        )

        awarder = DatasetPointsAwarder(app=self.app)
        awarded = awarder.award_points(user=user, dataset=dataset)

        self.assertEqual(len(awarded), 1)
        self.assertEqual(awarded[0].app, self.app)
        self.assertEqual(awarded[0].user, user)
        self.assertEqual(awarded[0].points, 10)
        self.assertEqual(awarded[0].awarded_for, 'First dataset bonus')
        self.assertEqual(awarded[0].content_object, dataset)

        self.assertEqual(UserPoints.objects.filter(user=user, content_type__isnull=False).count(), 1)

    @test_settings
    def test_awards_points_for_every_dataset_created_condition(self):
        user = self.create_user()
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form=observation_form, user=user)

        rule = PointRule.objects.create(
            app=self.app,
            name='Every dataset',
            points=1,
            awarded_for='Dataset created',
        )
        PointRuleCondition.objects.create(
            rule=rule,
            factor_type=FACTOR_DATASET_CREATED,
            operator='equals',
            value_json=True,
        )

        awarder = DatasetPointsAwarder(app=self.app)
        awarded = awarder.award_points(user=user, dataset=dataset)

        self.assertEqual(len(awarded), 1)
        self.assertEqual(awarded[0].app, self.app)
        self.assertEqual(awarded[0].user, user)
        self.assertEqual(awarded[0].points, 1)
        self.assertEqual(awarded[0].awarded_for, 'Dataset created')
        self.assertEqual(awarded[0].content_object, dataset)

    @test_settings
    def test_awards_points_for_first_species_in_polygon_even_if_not_first_user_dataset(self):
        user = self.create_user()
        observation_form = self.create_observation_form()

        # Existing dataset makes this NOT the first dataset for this user.
        self.create_dataset(observation_form=observation_form, user=user)

        dataset = self.create_dataset(
            observation_form=observation_form,
            user=user,
            taxon=self.lazy_taxon.as_json(),
        )

        polygon_b = self.create_polygon_for_dataset(dataset, name='Polygon B')

        rule = PointRule.objects.create(
            app=self.app,
            name='First user report of species A in polygon B',
            points=30,
            awarded_for='First report of species A in polygon B',
        )
        PointRuleCondition.objects.create(
            rule=rule,
            factor_type=FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER,
            operator='equals',
            value_json=True,
        )
        awarder = DatasetPointsAwarder(app=self.app)
        awarded = awarder.award_points(user=user, dataset=dataset)

        self.assertEqual(
            DatasetPointsAwarder(app=self.app)._build_context(user=user, dataset=dataset).get(FACTOR_IS_FIRST_DATASET_FOR_USER),
            False,
        )
        self.assertEqual(len(awarded), 1)
        self.assertEqual(awarded[0].app, self.app)
        self.assertEqual(awarded[0].user, user)
        self.assertEqual(awarded[0].points, 30)
        self.assertEqual(awarded[0].content_object, dataset)
        self.assertEqual(
            UserPoints.objects.filter(user=user, awarded_for='First report of species A in polygon B').count(),
            1,
        )

    @test_settings
    def test_does_not_award_points_if_species_already_reported_in_polygon(self):
        user = self.create_user()
        observation_form = self.create_observation_form()

        first_species_dataset = self.create_dataset(
            observation_form=observation_form,
            user=user,
            taxon=self.lazy_taxon.as_json(),
        )
        self.create_polygon_for_dataset(first_species_dataset, name='Polygon B')

        second_species_dataset = self.create_dataset(
            observation_form=observation_form,
            user=user,
            taxon=self.lazy_taxon.as_json(),
        )

        rule = PointRule.objects.create(
            app=self.app,
            name='First user report of species A in polygon B',
            points=30,
            awarded_for='First report of species A in polygon B (negative test)',
        )
        PointRuleCondition.objects.create(
            rule=rule,
            factor_type=FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER,
            operator='equals',
            value_json=True,
        )

        awarder = DatasetPointsAwarder(app=self.app)
        awarded = awarder.award_points(user=user, dataset=second_species_dataset)

        self.assertEqual(
            DatasetPointsAwarder(app=self.app)._build_context(user=user, dataset=second_species_dataset).get(
                FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER
            ),
            False,
        )
        self.assertEqual(len(awarded), 0)
        self.assertEqual(
            UserPoints.objects.filter(
                user=user,
                awarded_for='First report of species A in polygon B (negative test)',
            ).count(),
            0,
        )
