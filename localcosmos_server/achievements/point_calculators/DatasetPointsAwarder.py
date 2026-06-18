from localcosmos_server.achievements.point_calculators.RuleBasedPointsAwarder import RuleBasedPointsAwarder
from localcosmos_server.achievements.point_calculators.AwardingContext import DatasetAwardingContext

from localcosmos_server.geography.models import GeographyPolygon
from localcosmos_server.datasets.models import Dataset

class DatasetPointsAwarder(RuleBasedPointsAwarder):
    
    def award_points(self, user, dataset):
        if user is None:
            return []

        context = self._build_context(user=user, dataset=dataset)
        return self.award_points_for_context(user=user, content_object=dataset, context=context)

    def _build_context(self, user, dataset):

        matching_geographies = []
        if dataset.coordinates:
            matching_geographies = list(
                GeographyPolygon.objects.filter(geometry__intersects=dataset.coordinates)
            )

        is_first_user_dataset = False
        is_first_species_in_polygon_for_user = False
        if user is not None:
            is_first_user_dataset = not Dataset.objects.filter(app_uuid=self.app.uuid, user=user).exclude(pk=dataset.pk).exists()

            if dataset.name_uuid and matching_geographies:
                prior_species_dataset_exists = False

                for geography in matching_geographies:
                    geography_geometry = getattr(geography, 'geometry', None) or getattr(geography, 'polygon', None)

                    if geography_geometry is None:
                        continue

                    if Dataset.objects.filter(
                        app_uuid=self.app.uuid,
                        user=user,
                        name_uuid=dataset.name_uuid,
                        coordinates__intersects=geography_geometry,
                    ).exclude(pk=dataset.pk).exists():
                        prior_species_dataset_exists = True
                        break

                is_first_species_in_polygon_for_user = not prior_species_dataset_exists

        return DatasetAwardingContext.build(
            dataset=dataset,
            matching_geographies=matching_geographies,
            is_first_dataset_for_user=is_first_user_dataset,
            is_first_species_in_polygon_for_user=is_first_species_in_polygon_for_user,
        )