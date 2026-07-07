import os

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.datasets.models import Dataset
from localcosmos_server.achievements.models import UserPoints
from localcosmos_server.management.commands.import_beachexplorer_observations import (
    Command as ImportBeachexplorerObservationsCommand,
)


class Command(BaseCommand):
    help = 'Validate imported BeachExplorer observations, users, and point totals against the legacy Symfony database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of legacy observation rows to validate.',
        )
        parser.add_argument(
            '--only-legacy-user-id',
            type=int,
            default=None,
            help='Only validate observations that belong to this legacy pd_user.id.',
        )
        parser.add_argument(
            '--app-name',
            default='BeachExplorer',
            help='Local Cosmos app name that receives the imported observations. Default: BeachExplorer',
        )
        parser.add_argument(
            '--observation-form-name',
            default='Fundmeldung',
            help='Observation form name in ObservationForm.definition.name. Default: Fundmeldung',
        )
        parser.add_argument(
            '--legacy-host',
            default=os.environ.get('LEGACY_DB_HOST'),
            help='Legacy PostgreSQL host/service name (for Docker Compose, usually the service name).',
        )
        parser.add_argument(
            '--legacy-port',
            type=int,
            default=int(os.environ.get('LEGACY_DB_PORT', '5432')),
            help='Legacy PostgreSQL port. Default: 5432',
        )
        parser.add_argument(
            '--legacy-name',
            default=os.environ.get('LEGACY_DB_NAME'),
            help='Legacy PostgreSQL database name.',
        )
        parser.add_argument(
            '--legacy-user',
            default=os.environ.get('LEGACY_DB_USER'),
            help='Legacy PostgreSQL user.',
        )
        parser.add_argument(
            '--legacy-password',
            default=os.environ.get('LEGACY_DB_PASSWORD'),
            help='Legacy PostgreSQL password.',
        )
        parser.add_argument(
            '--legacy-sslmode',
            default=os.environ.get('LEGACY_DB_SSLMODE'),
            help='Optional PostgreSQL sslmode for legacy DB connection.',
        )

    def handle(self, *args, **options):
        legacy_db_config = ImportBeachexplorerObservationsCommand._get_legacy_db_config(self, options)
        app = ImportBeachexplorerObservationsCommand._get_target_app(self, options['app_name'])
        observation_form = ImportBeachexplorerObservationsCommand._get_observation_form(
            self,
            options['observation_form_name'],
        )

        self.stdout.write(
            f"Using legacy DB source {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )
        self.stdout.write('Starting validate_beachexplorer_import.')
        self.stdout.write(f'Target app: {app.name} (uid={app.uid})')
        self.stdout.write(
            f"Observation form: {observation_form.definition.get('name')} "
            f"(uuid={observation_form.uuid}, version={observation_form.version})"
        )

        observations = ImportBeachexplorerObservationsCommand._fetch_symfony_observations(
            self,
            legacy_db_config=legacy_db_config,
            limit=options['limit'],
            only_legacy_user_id=options['only_legacy_user_id'],
        )
        legacy_determination_ids = [row['determination_id'] for row in observations]
        points_by_determination = ImportBeachexplorerObservationsCommand._fetch_symfony_determination_points(
            self,
            legacy_db_config=legacy_db_config,
            determination_ids=legacy_determination_ids,
        )

        imported_datasets_by_determination = self._fetch_imported_datasets(
            app=app,
            observation_form=observation_form,
            determination_ids=legacy_determination_ids,
        )
        dataset_content_type = ContentType.objects.get_for_model(Dataset)

        self.stdout.write(
            f'Legacy observation rows found: {len(observations)} '
            f'(legacy points rows: {sum(len(rows) for rows in points_by_determination.values())})'
        )
        self.stdout.write(
            f'Imported datasets found: {sum(len(rows) for rows in imported_datasets_by_determination.values())}'
        )

        stats = {
            'processed': 0,
            'validated': 0,
            'missing_imports': 0,
            'duplicate_imports': 0,
            'user_mismatches': 0,
            'unmapped_legacy_users': 0,
            'point_sum_mismatches': 0,
            'legacy_points_total': 0,
            'new_points_total': 0,
        }
        problems = []

        for legacy_observation in observations:
            stats['processed'] += 1
            legacy_determination_id = legacy_observation['determination_id']
            legacy_user_id = legacy_observation.get('legacy_user_id')

            expected_user = ImportBeachexplorerObservationsCommand._find_local_user_from_legacy_user_id(
                self,
                legacy_user_id,
            )
            if expected_user is None:
                stats['unmapped_legacy_users'] += 1

            imported_datasets = imported_datasets_by_determination.get(legacy_determination_id, [])
            if not imported_datasets:
                stats['missing_imports'] += 1
                problems.append(
                    f'be_determination id={legacy_determination_id}: missing imported dataset.'
                )
                continue

            if len(imported_datasets) > 1:
                stats['duplicate_imports'] += 1
                problems.append(
                    f'be_determination id={legacy_determination_id}: '
                    f'found {len(imported_datasets)} imported datasets.'
                )

            dataset = imported_datasets[0]

            if expected_user is not None:
                expected_user_id = str(expected_user.uuid)
                actual_user_id = str(dataset.user_id) if dataset.user_id is not None else None
                if actual_user_id != expected_user_id:
                    stats['user_mismatches'] += 1
                    problems.append(
                        f'be_determination id={legacy_determination_id}: '
                        f'expected user {expected_user_id}, got {actual_user_id}.'
                    )
            elif dataset.user_id is not None:
                stats['user_mismatches'] += 1
                problems.append(
                    f'be_determination id={legacy_determination_id}: '
                    f'legacy user {legacy_user_id} has no LocalcosmosUser mapping, '
                    f'but imported dataset was assigned to {dataset.user_id}.'
                )

            legacy_points_total = self._sum_points(points_by_determination.get(legacy_determination_id, []))
            new_points_total = self._sum_new_points(
                app=app,
                dataset=dataset,
                content_type=dataset_content_type,
            )

            stats['legacy_points_total'] += legacy_points_total
            stats['new_points_total'] += new_points_total
            stats['validated'] += 1

            if legacy_points_total != new_points_total:
                stats['point_sum_mismatches'] += 1
                problems.append(
                    f'be_determination id={legacy_determination_id}: '
                    f'legacy points sum={legacy_points_total}, new points sum={new_points_total}.'
                )

        self.stdout.write('')
        self.stdout.write('Validation summary:')
        for key, value in stats.items():
            self.stdout.write(f'  {key}: {value}')

        if problems:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('Validation problems:'))
            for problem in problems[:50]:
                self.stdout.write(self.style.ERROR(f'  - {problem}'))

            if len(problems) > 50:
                self.stdout.write(self.style.ERROR(f'  - ... and {len(problems) - 50} more'))

            raise CommandError('BeachExplorer import validation failed.')

        self.stdout.write(self.style.SUCCESS('BeachExplorer import validation passed.'))

    def _fetch_imported_datasets(self, app, observation_form, determination_ids):
        if not determination_ids:
            return defaultdict(list)

        grouped = defaultdict(list)
        datasets = Dataset.objects.filter(
            app_uuid=app.uuid,
            observation_form=observation_form,
            data__legacyImport__source='beachexplorer',
            data__legacyImport__provider='symfony',
            data__legacyImport__determinationId__in=determination_ids,
        ).select_related('user')

        for dataset in datasets:
            legacy_import = dataset.data.get('legacyImport') if isinstance(dataset.data, dict) else None
            determination_id = None
            if isinstance(legacy_import, dict):
                determination_id = legacy_import.get('determinationId')

            if determination_id is None:
                continue

            grouped[determination_id].append(dataset)

        return grouped

    def _sum_points(self, point_rows):
        total = 0
        for row in point_rows:
            points = row.get('points')
            if points is not None:
                total += points

        return total

    def _sum_new_points(self, app, dataset, content_type):
        total = 0
        queryset = UserPoints.objects.filter(
            app=app,
            content_type=content_type,
            object_id=dataset.pk,
        )

        for user_point in queryset:
            if user_point.points is not None:
                total += user_point.points

        return total