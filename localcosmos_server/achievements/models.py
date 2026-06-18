from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from localcosmos_server.achievements.factor_types import FACTOR_TYPE_CHOICES
from localcosmos_server.achievements.factor_types import KNOWN_POINT_FACTOR_TYPES

from localcosmos_server.models import App

LocalcosmosUser = get_user_model()


class UserPointsManager(models.Manager):

    def award_user_points(self, app, user, points, awarded_for=None, content_object=None):
        if user is None:
            raise ValueError('Cannot award user points without a user.')

        user_points = self.model(
            app=app,
            user=user,
            points=points,
            awarded_for=awarded_for,
        )

        if content_object is not None:
            user_points.content_object = content_object

        user_points.save()
        return user_points


class UserPoints(models.Model):
    
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='user_points')
    
    user = models.ForeignKey(LocalcosmosUser, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    points = models.IntegerField(default=0)
    awarded_for = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = UserPointsManager()


# make point system totally generic and configurable in the backend
MATCH_MODE_CHOICES = (
    ('all', 'All conditions must match'),
    ('any', 'At least one condition must match'),
)


CONDITION_OPERATOR_CHOICES = (
    ('equals', 'Equals'),
    ('in', 'In list'),
    ('intersects', 'Intersects'),
)


class PointRule(models.Model):
    """
    Defines how many points a matching rule awards.

    Example:
    - code='first_taxon_in_geography'
    - points=10
    - match_mode='all'
      -> all related PointRuleCondition rows must match.
    """

    # point rules are app specific, so we can have different rules for different apps in the same database
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='point_rules')

    name = models.CharField(max_length=255)

    points = models.IntegerField(default=0)
    awarded_for = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)
    match_mode = models.CharField(max_length=10, choices=MATCH_MODE_CHOICES, default='all')
    position = models.IntegerField(default=0)

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    
    @property
    def match_mode_display(self):
        return dict(MATCH_MODE_CHOICES).get(self.match_mode, self.match_mode)

    def __str__(self):
        return f"{self.name} ({self.points})"

# multiple conditions possible. for example:
# - is species A
# - is first in geography B
class PointRuleCondition(models.Model):
    """
    A single condition/factor for a PointRule.

    This model supports both object-based and value-based factors:
    - object-based: species/geography/etc via content_object
    - value-based: scalar values/ranges in value_json
    """

    # The parent rule this condition belongs to.
    rule = models.ForeignKey(PointRule, on_delete=models.CASCADE, related_name='conditions')

    # Semantic factor name, e.g. species, geography, dataset_type.
    # The evaluator uses this to map input context to this condition.
    factor_type = models.CharField(max_length=100, choices=FACTOR_TYPE_CHOICES)

    # Comparison operation to apply for this factor.
    # Example: equals (exact match), in (membership), intersects (spatial overlap).
    operator = models.CharField(max_length=20, choices=CONDITION_OPERATOR_CHOICES, default='equals')

    # Generic relation target model for object-based matching.
    # Leave empty for pure value-based conditions.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)

    # Generic relation target primary key for object-based matching.
    object_id = models.PositiveIntegerField(null=True, blank=True)

    # Convenience accessor for the generic relation (content_type + object_id).
    content_object = GenericForeignKey('content_type', 'object_id')

    # JSON payload for value-based matching (scalar/list/range/etc).
    # Example: ["spring", "summer"] or {"min": 10, "max": 100}.
    value_json = models.JSONField(null=True, blank=True)

    # Optional ordering for deterministic evaluation/readability.
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('position', 'id')

    def clean(self):
        super().clean()

        if self.factor_type not in KNOWN_POINT_FACTOR_TYPES:
            allowed = ', '.join(sorted(KNOWN_POINT_FACTOR_TYPES))
            raise ValidationError({
                'factor_type': f'Unsupported factor_type "{self.factor_type}". Allowed values: {allowed}'
            })

    def __str__(self):
        return f"{self.rule.name}:{self.factor_type}:{self.operator}"

