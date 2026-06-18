from dataclasses import dataclass, field

from localcosmos_server.achievements.factor_types import EVENT_DATASET_CREATED
from localcosmos_server.achievements.factor_types import FACTOR_DATASET
from localcosmos_server.achievements.factor_types import FACTOR_DATASET_CREATED
from localcosmos_server.achievements.factor_types import FACTOR_GEOGRAPHY
from localcosmos_server.achievements.factor_types import FACTOR_IS_FIRST_DATASET_FOR_USER
from localcosmos_server.achievements.factor_types import FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER
from localcosmos_server.achievements.factor_types import FACTOR_TAXON
from localcosmos_server.achievements.factor_types import REQUIRED_FACTORS_BY_EVENT


@dataclass
class AwardingContext:
    """
    Standardized context object passed to rule-based point awarders.

    - event: semantic event key, e.g. 'dataset_created'
    - content_object: optional primary object related to the event
    - values: factor payload used by PointRuleCondition.factor_type lookups
    """

    event: str
    content_object: object = None
    values: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.event:
            raise ValueError('AwardingContext.event is required.')

    def validate(self):
        required_factors = REQUIRED_FACTORS_BY_EVENT.get(self.event, [])
        missing = [factor for factor in required_factors if factor not in self.values]

        if missing:
            missing_display = ', '.join(sorted(missing))
            raise ValueError(
                f'Invalid awarding context for event "{self.event}": missing factors: {missing_display}'
            )

        return True

    def set_factor(self, factor_type, value):
        self.values[factor_type] = value

    def get(self, factor_type, default=None):
        return self.values.get(factor_type, default)

    def to_dict(self):
        payload = {
            'event': self.event,
            'content_object': self.content_object,
        }
        payload.update(self.values)
        return payload


class DatasetAwardingContext(AwardingContext):
    """
    Helper context for dataset-created events.
    """

    @classmethod
    def build(
        cls,
        dataset,
        matching_geographies=None,
        is_first_dataset_for_user=False,
        is_first_species_in_polygon_for_user=False,
    ):
        if matching_geographies is None:
            matching_geographies = []

        taxon_values = [
            value for value in (
                str(dataset.name_uuid) if dataset.name_uuid else None,
                dataset.taxon_nuid,
                dataset.taxon_latname,
            )
            if value not in (None, '')
        ]

        values = {
            FACTOR_DATASET: dataset,
            FACTOR_GEOGRAPHY: matching_geographies,
            FACTOR_TAXON: taxon_values,
            FACTOR_IS_FIRST_DATASET_FOR_USER: is_first_dataset_for_user,
            FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER: is_first_species_in_polygon_for_user,
            FACTOR_DATASET_CREATED: True,
        }

        context = cls(
            event=EVENT_DATASET_CREATED,
            content_object=dataset,
            values=values,
        )
        context.validate()
        return context
