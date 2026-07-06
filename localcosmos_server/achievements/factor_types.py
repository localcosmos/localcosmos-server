from localcosmos_server.datasets.models import Dataset
from localcosmos_server.geography.models import GeographyPolygon

EVENT_DATASET_CREATED = 'dataset_created'

FACTOR_DATASET = 'dataset'
FACTOR_GEOGRAPHY = 'geography'
FACTOR_TAXON = 'taxon'
FACTOR_IS_FIRST_DATASET_FOR_USER = 'is_first_dataset_for_user'
FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER = 'is_first_species_in_polygon_for_user'
FACTOR_DATASET_CREATED = 'dataset_created'

DATASET_EVENT_FACTORS = (
    FACTOR_DATASET,
    FACTOR_GEOGRAPHY,
    FACTOR_TAXON,
    FACTOR_IS_FIRST_DATASET_FOR_USER,
    FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER,
    FACTOR_DATASET_CREATED,
)

REQUIRED_FACTORS_BY_EVENT = {
    EVENT_DATASET_CREATED: DATASET_EVENT_FACTORS,
}

KNOWN_POINT_FACTOR_TYPES = set(DATASET_EVENT_FACTORS)

FACTOR_TYPE_LABELS = {
    FACTOR_DATASET: 'Dataset',
    FACTOR_GEOGRAPHY: 'Inside Geography',
    FACTOR_TAXON: 'Taxon',
    FACTOR_IS_FIRST_DATASET_FOR_USER: 'Is first dataset for user',
    FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER: 'Is first species in any polygon',
    FACTOR_DATASET_CREATED: 'Dataset created',
}

FACTOR_TYPE_CHOICES = tuple(
    (factor, FACTOR_TYPE_LABELS.get(factor, factor.replace('_', ' ').title()))
    for factor in DATASET_EVENT_FACTORS
)

OBJECT_MODELS_BY_FACTOR_TYPE = {
	FACTOR_DATASET: (Dataset,),
	FACTOR_GEOGRAPHY: (GeographyPolygon,),
}