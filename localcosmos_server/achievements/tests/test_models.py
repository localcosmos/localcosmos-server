from django.core.exceptions import ValidationError
from django.test import TestCase

from localcosmos_server.achievements.factor_types import FACTOR_DATASET
from localcosmos_server.achievements.factor_types import FACTOR_DATASET_CREATED
from localcosmos_server.achievements.models import PointRule, PointRuleCondition, UserPoints
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser


class TestUserPointsManager(WithApp, WithUser, TestCase):

	@test_settings
	def test_award_user_points_requires_user(self):
		with self.assertRaises(ValueError):
			UserPoints.objects.award_user_points(self.app, None, 10, awarded_for='test')

	@test_settings
	def test_award_user_points_saves_points(self):
		user = self.create_user()

		user_points = UserPoints.objects.award_user_points(
			self.app,
			user,
			25,
			awarded_for='rule-a',
			content_object=user,
		)

		self.assertEqual(user_points.app, self.app)
		self.assertEqual(user_points.user, user)
		self.assertEqual(user_points.points, 25)
		self.assertEqual(user_points.awarded_for, 'rule-a')
		self.assertEqual(user_points.content_object, user)
		self.assertIsNotNone(user_points.timestamp)

		db_user_points = UserPoints.objects.get(pk=user_points.pk)
		self.assertEqual(db_user_points.content_object, user)


class TestPointRule(WithApp, TestCase):

	@test_settings
	def test_str(self):
		rule = PointRule.objects.create(
			app=self.app,
			name='First dataset',
			points=10,
			awarded_for='First dataset bonus',
		)

		self.assertEqual(str(rule), 'First dataset (10)')


class TestPointRuleCondition(WithApp, TestCase):

	def create_rule(self):
		return PointRule.objects.create(
			app=self.app,
			name='Any dataset',
			points=5,
			awarded_for='Any dataset',
		)

	@test_settings
	def test_clean_rejects_unknown_factor_type(self):
		rule = self.create_rule()
		condition = PointRuleCondition(
			rule=rule,
			factor_type='unknown_factor',
			operator='equals',
		)

		with self.assertRaises(ValidationError) as ctx:
			condition.full_clean()

		self.assertIn('factor_type', ctx.exception.message_dict)

	@test_settings
	def test_clean_accepts_known_factor_type(self):
		rule = self.create_rule()
		condition = PointRuleCondition(
			rule=rule,
			factor_type=FACTOR_DATASET_CREATED,
			operator='equals',
		)

		condition.full_clean()

	@test_settings
	def test_ordering_by_position_then_id(self):
		rule = self.create_rule()

		second = PointRuleCondition.objects.create(
			rule=rule,
			factor_type=FACTOR_DATASET,
			operator='equals',
			position=2,
		)

		first = PointRuleCondition.objects.create(
			rule=rule,
			factor_type=FACTOR_DATASET,
			operator='equals',
			position=1,
		)

		conditions = list(PointRuleCondition.objects.filter(rule=rule))
		self.assertEqual(conditions, [first, second])

	@test_settings
	def test_str(self):
		rule = self.create_rule()
		condition = PointRuleCondition.objects.create(
			rule=rule,
			factor_type=FACTOR_DATASET_CREATED,
			operator='equals',
			position=1,
		)

		self.assertEqual(str(condition), 'Any dataset:dataset_created:equals')
