from django.test import TestCase
from django.urls import reverse

from localcosmos_server.achievements.factor_types import (
    FACTOR_DATASET_CREATED,
    FACTOR_IS_FIRST_DATASET_FOR_USER,
)
from localcosmos_server.achievements.models import PointRule, PointRuleCondition
from localcosmos_server.models import App
from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithApp, WithUser


@test_settings
class TestListAchievements(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.user = self.create_user()
        self.superuser = self.create_superuser()

        self.url_kwargs = {
            'app_uid': self.app.uid,
        }

    def test_get_requires_login(self):
        response = self.client.get(reverse('achievements:achievements_list', kwargs=self.url_kwargs))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('log_in'), response.url)

    def test_get_permission_denied_for_regular_user(self):
        self.client.login(username=self.test_username, password=self.test_password)

        response = self.client.get(reverse('achievements:achievements_list', kwargs=self.url_kwargs))

        self.assertEqual(response.status_code, 403)

    def test_get_superuser(self):
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        response = self.client.get(reverse('achievements:achievements_list', kwargs=self.url_kwargs))

        self.assertEqual(response.status_code, 200)


@test_settings
class TestGetPointRules(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        self.ajax_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }

        self.url_kwargs = {
            'app_uid': self.app.uid,
        }

    def test_get_requires_ajax(self):
        response = self.client.get(reverse('achievements:point_rules_list', kwargs=self.url_kwargs))

        self.assertEqual(response.status_code, 400)

    def test_get_context_data_filters_and_orders_point_rules(self):
        PointRule.objects.create(
            app=self.app,
            name='Rule B',
            points=2,
            awarded_for='Rule B reason',
            position=2,
        )
        rule_a = PointRule.objects.create(
            app=self.app,
            name='Rule A',
            points=1,
            awarded_for='Rule A reason',
            position=1,
        )

        other_app = App.objects.create(
            name='Other app',
            uid='achievements-test-other-app-rules',
            primary_language=self.app.primary_language,
            published_version_path=self.app.published_version_path,
        )
        PointRule.objects.create(
            app=other_app,
            name='Other app rule',
            points=9,
            awarded_for='Other app rule reason',
            position=0,
        )

        response = self.client.get(
            reverse('achievements:point_rules_list', kwargs=self.url_kwargs),
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['point_rules']), [rule_a, PointRule.objects.get(app=self.app, name='Rule B')])
        self.assertEqual(response.context['point_rules_ctype'].model_class(), PointRule)


@test_settings
class TestManagePointRule(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        self.rule = PointRule.objects.create(
            app=self.app,
            name='Existing rule',
            points=10,
            awarded_for='Existing reason',
            position=1,
        )

        self.ajax_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }

    def test_get_requires_ajax(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }

        response = self.client.get(reverse('achievements:add_point_rule', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 400)

    def test_get_add_context(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }

        response = self.client.get(reverse('achievements:add_point_rule', kwargs=url_kwargs), **self.ajax_headers)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['point_rule'])
        self.assertFalse(response.context['success'])

    def test_get_edit_context(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'rule_id': self.rule.id,
        }

        response = self.client.get(reverse('achievements:edit_point_rule', kwargs=url_kwargs), **self.ajax_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['point_rule'], self.rule)
        self.assertFalse(response.context['success'])

    def test_post_add_point_rule(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }

        response = self.client.post(
            reverse('achievements:add_point_rule', kwargs=url_kwargs),
            {
                'name': 'Created rule',
                'points': 42,
                'awarded_for': 'Created reason',
                'is_active': True,
                'match_mode': 'all',
                'valid_from': '',
                'valid_to': '',
                'input_language': self.app.primary_language,
            },
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        created_rule = PointRule.objects.get(app=self.app, name='Created rule')
        self.assertEqual(created_rule.points, 42)
        self.assertEqual(created_rule.awarded_for, 'Created reason')

    def test_post_edit_point_rule(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'rule_id': self.rule.id,
        }

        response = self.client.post(
            reverse('achievements:edit_point_rule', kwargs=url_kwargs),
            {
                'name': 'Updated rule',
                'points': 5,
                'awarded_for': 'Updated reason',
                'is_active': False,
                'match_mode': 'any',
                'valid_from': '',
                'valid_to': '',
                'input_language': self.app.primary_language,
            },
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        self.rule.refresh_from_db()
        self.assertEqual(self.rule.name, 'Updated rule')
        self.assertEqual(self.rule.points, 5)
        self.assertEqual(self.rule.awarded_for, 'Updated reason')
        self.assertFalse(self.rule.is_active)
        self.assertEqual(self.rule.match_mode, 'any')


@test_settings
class TestManageDatasetCondition(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        self.rule = PointRule.objects.create(
            app=self.app,
            name='Rule',
            points=10,
            awarded_for='Reason',
            position=1,
        )

        self.condition = PointRuleCondition.objects.create(
            rule=self.rule,
            factor_type=FACTOR_DATASET_CREATED,
            operator='equals',
            value_json=True,
            position=1,
        )

        self.ajax_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }

    def test_get_requires_ajax(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'rule_id': self.rule.id,
        }

        response = self.client.get(reverse('achievements:add_dataset_condition', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 400)

    def test_get_add_context(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'rule_id': self.rule.id,
        }

        response = self.client.get(reverse('achievements:add_dataset_condition', kwargs=url_kwargs), **self.ajax_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['point_rule'], self.rule)
        self.assertIsNone(response.context['condition'])

    def test_post_add_dataset_condition(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'rule_id': self.rule.id,
        }

        response = self.client.post(
            reverse('achievements:add_dataset_condition', kwargs=url_kwargs),
            {
                'factor_type': FACTOR_IS_FIRST_DATASET_FOR_USER,
            },
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        condition = PointRuleCondition.objects.filter(rule=self.rule).exclude(pk=self.condition.pk).first()
        self.assertIsNotNone(condition)
        self.assertEqual(condition.factor_type, FACTOR_IS_FIRST_DATASET_FOR_USER)
        self.assertEqual(condition.operator, 'equals')
        self.assertEqual(condition.value_json, True)

    def test_post_edit_dataset_condition(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'rule_id': self.rule.id,
            'condition_id': self.condition.id,
        }

        response = self.client.post(
            reverse('achievements:edit_dataset_condition', kwargs=url_kwargs),
            {
                'factor_type': FACTOR_IS_FIRST_DATASET_FOR_USER,
            },
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        self.condition.refresh_from_db()
        self.assertEqual(self.condition.factor_type, FACTOR_IS_FIRST_DATASET_FOR_USER)


@test_settings
class TestDeleteViews(WithApp, WithUser, TestCase):

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.client.login(username=self.test_superuser_username, password=self.test_password)

        self.rule = PointRule.objects.create(
            app=self.app,
            name='Delete rule',
            points=10,
            awarded_for='Delete reason',
        )
        self.condition = PointRuleCondition.objects.create(
            rule=self.rule,
            factor_type=FACTOR_DATASET_CREATED,
            operator='equals',
            value_json=True,
        )

        self.ajax_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }

    def test_delete_point_rule(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'pk': self.rule.id,
        }

        response = self.client.post(reverse('achievements:delete_point_rule', kwargs=url_kwargs), **self.ajax_headers)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['deleted'])
        self.assertEqual(response.context['deleted_object_id'], self.rule.id)
        self.assertFalse(PointRule.objects.filter(pk=self.rule.id).exists())

    def test_delete_point_rule_condition(self):
        url_kwargs = {
            'app_uid': self.app.uid,
            'pk': self.condition.id,
        }

        response = self.client.post(
            reverse('achievements:delete_point_rule_condition', kwargs=url_kwargs),
            **self.ajax_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['deleted'])
        self.assertEqual(response.context['deleted_object_id'], self.condition.id)
        self.assertFalse(PointRuleCondition.objects.filter(pk=self.condition.id).exists())
