from django.db import models as django_models
from django.db.models import Q
from django.utils import timezone

from localcosmos_server.achievements.models import PointRule, UserPoints
from localcosmos_server.achievements.point_calculators.BasePointAwarder import BasePointsAwarder


class RuleBasedPointsAwarder(BasePointsAwarder):
    """
    Generic awarder that evaluates active PointRule entries against an awarding context.

    Context keys are matched to PointRuleCondition.factor_type. Input can be either
    a plain dict or any object that exposes a to_dict() method.
    """

    def get_active_rules(self):
        now = timezone.now()
        queryset = PointRule.objects.filter(
            app=self.app,
            is_active=True,
        ).filter(
            Q(valid_from__isnull=True) | Q(valid_from__lte=now),
            Q(valid_to__isnull=True) | Q(valid_to__gte=now),
        )

        return queryset.prefetch_related('conditions').order_by('-position', 'id')

    def award_points_for_context(self, user, content_object, context):
        normalized_context = self._normalize_context(context)
        awarded = []

        for rule in self.get_active_rules():
            if self.rule_matches(rule, normalized_context):
                user_points = UserPoints.objects.award_user_points(
                    app=rule.app,
                    user=user,
                    points=rule.points,
                    awarded_for=rule.awarded_for,
                    content_object=content_object,
                )
                awarded.append(user_points)

        return awarded

    def _normalize_context(self, context):
        if hasattr(context, 'validate') and callable(context.validate):
            context.validate()

        if hasattr(context, 'to_dict') and callable(context.to_dict):
            return context.to_dict()

        if isinstance(context, dict):
            return context

        raise ValueError('Context must be a dict or provide a to_dict() method.')

    def rule_matches(self, rule, context):
        conditions = list(rule.conditions.all())

        if not conditions:
            return False

        matches = [self.condition_matches(condition, context) for condition in conditions]

        if rule.match_mode == 'any':
            return any(matches)

        return all(matches)

    def condition_matches(self, condition, context):
        actual = context.get(condition.factor_type)
        expected_object = condition.content_object if condition.content_type_id and condition.object_id else None
        expected_value = condition.value_json

        if condition.operator == 'equals':
            if expected_object is not None:
                return self._matches_object(actual, expected_object)
            return self._matches_equals(actual, expected_value)

        if condition.operator == 'in':
            return self._matches_in(actual, expected_value)

        if condition.operator == 'intersects':
            if expected_object is None:
                return False
            return self._matches_intersects(actual, expected_object)

        return False

    def _as_sequence(self, value):
        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):
            return list(value)

        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes, dict)):
            try:
                return list(value)
            except TypeError:
                return [value]

        return [value]

    def _objects_equal(self, left, right):
        if not isinstance(left, django_models.Model) or not isinstance(right, django_models.Model):
            return False

        return left._meta.label == right._meta.label and left.pk == right.pk

    def _matches_object(self, actual, expected_object):
        for item in self._as_sequence(actual):
            if self._objects_equal(item, expected_object):
                return True

        return False

    def _matches_equals(self, actual, expected_value):
        if isinstance(actual, (list, tuple, set)):
            return expected_value in actual

        return actual == expected_value

    def _matches_in(self, actual, expected_value):
        expected_values = expected_value if isinstance(expected_value, list) else [expected_value]

        if isinstance(actual, (list, tuple, set)):
            return any(item in expected_values for item in actual)

        return actual in expected_values

    def _matches_intersects(self, actual, expected_object):
        # Exact object match for prepared context collections (for example matching geographies).
        if self._matches_object(actual, expected_object):
            return True

        expected_geometry = getattr(expected_object, 'geometry', None)
        if expected_geometry is None:
            expected_geometry = getattr(expected_object, 'polygon', None)

        if expected_geometry is not None:

            # Example: context contains dataset with coordinates.
            if hasattr(actual, 'coordinates') and actual.coordinates is not None:
                return expected_geometry.intersects(actual.coordinates)

            # Example: context contains a geometry directly.
            if hasattr(actual, 'intersects'):
                try:
                    return actual.intersects(expected_geometry)
                except Exception:
                    return False

            # Example: context contains a list/queryset of objects with polygon field.
            for item in self._as_sequence(actual):
                item_geometry = getattr(item, 'geometry', None)
                if item_geometry is None:
                    item_geometry = getattr(item, 'polygon', None)

                if item_geometry is not None:
                    if item_geometry.intersects(expected_geometry):
                        return True

        return False
