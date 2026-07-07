# Migration scope (draft):
# import observatoins one-by-one
# - legacy_observatoin.user_id matches LocalcosmosUser.legacy_user_info['symfony']['id']
# - The observation form that is used is: "Fundmeldung"
# - his observatoin form has the following Fields:
#   - "Art"
#   - "Datum"
#   - "Ort"
#   - "Anzahl"
#   - "Zustand"
#   - "Morphotype"
#   - "Zurückgelegte Distanz" - this will not be imported, as it seems have to been deprecated in the legacy system
#   - "Fotos"
#   - "Kommentar"
#
# The observation Form is submited by the App and stored as a document (json) in the database
# The legacy observation data will be mapped to the new observation form and stored in the database as a new observation document.
# The BeachExplorer has to be built once, and the observatoin form then has to be copied over

import os
import json

from collections import defaultdict
from datetime import datetime, time, timezone as dt_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from localcosmos_server.models import LocalcosmosUser, App
from localcosmos_server.datasets.models import Dataset, ObservationForm

from localcosmos_server.achievements.models import UserPoints

# a map for taxa that do not exist 1:1 in the new database. For example morphotypes, dead specimens, etc. 
TAXA_MAP = {
    '(eggs)' : {
        
    },
    '(t)' : {
        'Zustand': 'tot',
    }
}

AWARDED_FOR_MAPPING = {
    'point.description.bonus': 'Bonuspunkte',
    'point.description.normal': 'Fundmeldung',
}

LEGACY_MORPHOTYPES = [
    '(†)',
    '(13./14. Jh)', # probably no morphotype
    '(15./18. Jh)', # probably no morphotype
    '(17./18. Jh)', # probably no morphotype
    '(aculeus)',
    '(ad pile)',
    '(adult)',
    '(ala)',
    '(Alae)',
    '(ala feminae)',
    '(ala forma obscura)',
    '(ala iuvenilis)',
    '(ala masculi)',
    '(ala, var)',
    '(auris)',
    '(Auris)',
    '(bill)',
    '(bones)',
    '(burrow)',
    '(Caninus)',
    '(Carapax)',
    '(Chela)',
    '(Clavicula)',
    '(closed)',
    '(colony)',
    '(coloration)',
    '(Costa)',
    '(cranial parts)',
    '(cranium)',
    '(Cranium)',
    '(cuttlebone)',
    '(damage)',
    '(Dens)',
    '(Dentale)',
    '(Digitus)',
    '(discoloration)',
    '(Duplikatur)',
    '(eggs)',
    '(erosion)',
    '(Exuvie)',
    '(faeces)',
    '(Faeces)',
    '(feet)',
    '(foam)',
    '(fossil)',
    '(fossil spine)',
    '(Fraktur)',
    '(gaul)',
    '(gills)',
    '(Gladius)',
    '(hole)',
    '(holes)',
    '(holes, young)',
    '(Humerus)',
    '(Hyoid)',
    '(juvenil)',
    '(juvenile)',
    '(juv pile)',
    '(Kokon)',
    '(large hole)',
    '(larva)',
    '(Larva)',
    '(Larvae)',
    '(Laterna)',
    '(leg)',
    '(Lux)',
    '(male)',
    '(Mandibulae)',
    '(Mandibulare)',
    '(Margarita)',
    '(= mariae)',
    '(mariae)',
    '(marking)',
    '(Molar)',
    '(monstrosity)',
    '(Operculum)',
    '(Os penis)',
    '(Ossa)',
    '(Ossa longa)',
    '(Otolith)',
    '(ovum)',
    '(Ovum)',
    '(Parasit)',
    '(pellets)',
    '(Pelvis)',
    '(phylloid)',
    '(pigment)',
    '(pile)',
    '(plastron)',
    '(Plumulae)',
    '(Polyp)',
    '(Praeoperculare)',
    '(primaries)',
    '(primary coverts)',
    '(Quadratum)',
    '(rest)',
    '(rhizoid)',
    '((rhizome)',
    '(Ring)',
    '(scales)',
    '(Scapula)',
    '(Scoliosis)',
    '(Scutum)',
    '(seaball)',
    '(secondaries)',
    '(secondary coverts)',
    '(septemradiatum)',
    '(Sipho)',
    '(small, shaggy)',
    '(small, smooth)',
    '(small, wharty)',
    '(solid)',
    '(spiculae)',
    '(Sternum)',
    '(t)',
    '(tail)',
    '(tail feathers)',
    '(Tergit)',
    '(tertials)',
    '(Torf)',
    '(tot)',
    '(track)',
    '(tracks)',
    '(transmitter)',
    '(tube)',
    '(tube shell)',
    '(tubular)',
    '(Tunica)',
    '(tunnel)',
    '(varieties)',
    '(variety)',
    '(Vertebrae)',
    '(vertebral disc)',
    '(Vertrebrae)',
]

TARGET_OBSERVATION_FORM_NAME = 'Fundmeldung'

class Command(BaseCommand):
    help = 'Import BeachExplorer observations and user points from Symfony legacy database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of legacy observation rows to process.',
        )
        parser.add_argument(
            '--only-legacy-user-id',
            type=int,
            default=None,
            help='Only import observations that belong to this legacy pd_user.id.',
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Persist imported datasets and user points.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without writing changes. This is the default behavior unless --commit is provided.',
        )
        parser.add_argument(
            '--app-name',
            default='BeachExplorer',
            help='Local Cosmos app name that receives imported observations. Default: BeachExplorer',
        )
        parser.add_argument(
            '--observation-form-name',
            default=TARGET_OBSERVATION_FORM_NAME,
            help=f'Observation form name in ObservationForm.definition.name. Default: {TARGET_OBSERVATION_FORM_NAME}',
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
        if options['commit'] and options['dry_run']:
            raise CommandError('Use either --commit or --dry-run, not both.')

        commit = options['commit'] and not options['dry_run']
        self._species_lookup_stub_warned = False

        legacy_db_config = self._get_legacy_db_config(options)
        app = self._get_target_app(options['app_name'])
        observation_form = self._get_observation_form(options['observation_form_name'])
        observation_field_map = self._build_observation_form_field_map(observation_form)

        self.stdout.write(
            f"Using legacy DB source {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )
        self.stdout.write(
            f"Starting import_beachexplorer_observations in {'COMMIT' if commit else 'DRY-RUN'} mode."
        )
        self.stdout.write(f'Target app: {app.name} (uid={app.uid})')
        self.stdout.write(
            f"Observation form: {observation_form.definition.get('name')} "
            f"(uuid={observation_form.uuid}, version={observation_form.version})"
        )

        observations = self._fetch_symfony_observations(
            legacy_db_config=legacy_db_config,
            limit=options['limit'],
            only_legacy_user_id=options['only_legacy_user_id'],
        )

        legacy_determination_ids = [row['determination_id'] for row in observations]
        points_by_determination = self._fetch_symfony_determination_points(
            legacy_db_config=legacy_db_config,
            determination_ids=legacy_determination_ids,
        )

        self.stdout.write(
            f'Legacy observation rows found: {len(observations)} '
            f'(legacy points rows: {sum(len(rows) for rows in points_by_determination.values())})'
        )

        stats = {
            'processed': 0,
            'datasets_created': 0,
            'datasets_existing': 0,
            'points_created': 0,
            'skipped_missing_user': 0,
            'skipped_missing_observation': 0,
            'errors': 0,
        }
        unmatched_species = defaultdict(lambda: {
            'count': 0,
            'legacy_species_ids': set(),
            'determination_ids': [],
        })

        for legacy_observation in observations:
            stats['processed'] += 1
            legacy_determination_id = legacy_observation['determination_id']

            try:
                local_user = self._find_local_user_from_legacy_user_id(
                    legacy_observation.get('legacy_user_id')
                )

                if local_user is None:
                    stats['skipped_missing_user'] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping be_determination id={legacy_determination_id}: '
                            'no LocalcosmosUser mapped via legacy_user_info.symfony.id. '
                            'Run import_symfony_users.py first.'
                        )
                    )
                    continue

                legacy_species_payload = {
                    'legacy_species_id': legacy_observation.get('legacy_species_id'),
                    'sciencename': legacy_observation.get('species_sciencename'),
                }

                taxon_payload = self.lookup_species_in_backbone_taxonomy(
                    app=app,
                    legacy_species_payload=legacy_species_payload,
                )

                if not taxon_payload:
                    species_name = (legacy_observation.get('species_sciencename') or '').strip() or 'UNKNOWN'
                    unresolved = unmatched_species[species_name]
                    unresolved['count'] += 1
                    legacy_species_id = legacy_observation.get('legacy_species_id')
                    if legacy_species_id is not None:
                        unresolved['legacy_species_ids'].add(legacy_species_id)
                    unresolved['determination_ids'].append(legacy_determination_id)

                dataset_data = self._build_dataset_data(
                    legacy_observation=legacy_observation,
                    observation_form=observation_form,
                    observation_field_map=observation_field_map,
                    taxon_payload=taxon_payload,
                )

                if not dataset_data:
                    stats['skipped_missing_observation'] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping be_determination id={legacy_determination_id}: no importable payload.'
                        )
                    )
                    continue

                dataset, created = self._create_or_get_dataset(
                    app=app,
                    observation_form=observation_form,
                    user=local_user,
                    dataset_data=dataset_data,
                    legacy_observation=legacy_observation,
                    commit=commit,
                )

                if created:
                    stats['datasets_created'] += 1
                else:
                    stats['datasets_existing'] += 1

                if dataset is None:
                    continue

                created_points = self._create_user_points_for_observation(
                    app=app,
                    dataset=dataset,
                    fallback_user=local_user,
                    determination_points=points_by_determination.get(legacy_determination_id, []),
                    commit=commit,
                )
                stats['points_created'] += created_points

            except Exception as exc:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed be_determination id={legacy_determination_id}: {exc}'
                    )
                )

        self.stdout.write('')
        self.stdout.write('Import summary:')
        for key, value in stats.items():
            self.stdout.write(f'  {key}: {value}')

        if unmatched_species:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    f'Species not found in backbone taxonomy: {len(unmatched_species)} unique names'
                )
            )
            for species_name in sorted(unmatched_species.keys()):
                unresolved = unmatched_species[species_name]
                legacy_species_ids = sorted(unresolved['legacy_species_ids'])
                determination_ids = unresolved['determination_ids']
                preview_ids = ', '.join(str(pk) for pk in determination_ids[:10])
                if len(determination_ids) > 10:
                    preview_ids += ', ...'

                self.stdout.write(
                    '  - '
                    f'{species_name}: {unresolved["count"]}x, '
                    f'legacy_species_ids={legacy_species_ids or [None]}, '
                    f'determination_ids=[{preview_ids}]'
                )

        if not commit:
            self.stdout.write(
                self.style.WARNING('Dry-run only. Re-run with --commit to persist changes.')
            )

    def _get_target_app(self, app_name):
        app = App.objects.filter(name=app_name).first()
        if app:
            return app

        app = App.objects.filter(name__iexact=app_name).first()
        if app:
            return app

        app = App.objects.filter(uid=app_name).first()
        if app:
            return app

        raise CommandError(
            f'Could not find App with name/uid "{app_name}".'
        )

    def _get_observation_form(self, form_name):
        exact = ObservationForm.objects.filter(definition__name=form_name).order_by('-version', '-pk').first()
        if exact:
            return exact

        wanted = (form_name or '').strip().casefold()
        for observation_form in ObservationForm.objects.order_by('-version', '-pk'):
            name = (observation_form.definition or {}).get('name')
            if isinstance(name, str) and name.strip().casefold() == wanted:
                return observation_form

        raise CommandError(
            f'Could not find ObservationForm with definition.name "{form_name}".'
        )

    def _build_observation_form_field_map(self, observation_form):
        field_map = {
            'by_role': {},
            'by_label': {},
        }

        for field in observation_form.definition.get('fields', []):
            role = field.get('role')
            if role and role not in field_map['by_role']:
                field_map['by_role'][role] = field.get('uuid')

            label = ((field.get('definition') or {}).get('label') or '').strip().casefold()
            if label:
                field_map['by_label'][label] = field.get('uuid')

        return field_map

    def _find_observation_field_uuid(self, observation_field_map, role=None, labels=None):
        if role:
            role_uuid = observation_field_map['by_role'].get(role)
            if role_uuid:
                return role_uuid

        if labels:
            for label in labels:
                lookup = (label or '').strip().casefold()
                uuid = observation_field_map['by_label'].get(lookup)
                if uuid:
                    return uuid

        return None

    def _build_dataset_data(self, legacy_observation, observation_form, observation_field_map, taxon_payload=None):
        data = {}

        taxon_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            role='taxonomicReference',
            labels=['Art', 'Taxon', 'Species'],
        )

        if taxon_field_uuid and taxon_payload:
            data[taxon_field_uuid] = taxon_payload

        temporal_payload = self._build_temporal_payload(legacy_observation.get('observation_date'))
        temporal_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            role='temporalReference',
            labels=['Datum', 'Zeitpunkt'],
        )
        if temporal_field_uuid and temporal_payload:
            data[temporal_field_uuid] = temporal_payload

        point_feature = self._build_point_feature(legacy_observation.get('point_geojson'))
        geographic_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            role='geographicReference',
            labels=['Ort', 'Punkt'],
        )
        if geographic_field_uuid and point_feature:
            data[geographic_field_uuid] = point_feature

        amount_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            labels=['Anzahl', 'Menge'],
        )
        if amount_field_uuid and legacy_observation.get('amount') is not None:
            data[amount_field_uuid] = int(legacy_observation['amount'])

        morphotype = self._extract_morphotype(legacy_observation.get('species_sciencename'))

        morphotype_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            labels=['Morphotype'],
        )
        if morphotype_field_uuid and morphotype is not None:
            data[morphotype_field_uuid] = morphotype

        condition_value = self._legacy_condition_value(morphotype)
        condition_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            labels=['Zustand'],
        )
        if condition_field_uuid and condition_value is not None:
            data[condition_field_uuid] = condition_value

        comment_field_uuid = self._find_observation_field_uuid(
            observation_field_map,
            labels=['Kommentar'],
        )
        if comment_field_uuid:
            data[comment_field_uuid] = self._build_legacy_comment(legacy_observation, taxon_payload)

        data['legacyImport'] = {
            'source': 'beachexplorer',
            'provider': 'symfony',
            'determinationId': legacy_observation.get('determination_id'),
            'speciesId': legacy_observation.get('legacy_species_id'),
            'speciesSciencename': legacy_observation.get('species_sciencename'),
            'speciesMatched': bool(taxon_payload),
            'status': legacy_observation.get('legacy_status'),
            'type': legacy_observation.get('legacy_type'),
            'oldspeciesids': legacy_observation.get('oldspeciesids'),
            'address': legacy_observation.get('address'),
            'distance': legacy_observation.get('distance'),
        }

        return data

    def _build_legacy_comment(self, legacy_observation, taxon_payload):
        legacy_species_name = legacy_observation.get('species_sciencename') or 'unknown'
        if taxon_payload:
            return f'Imported from legacy be_determination #{legacy_observation.get("determination_id")}'

        return (
            f'Imported from legacy be_determination #{legacy_observation.get("determination_id")}. '
            f'Species mapping pending for "{legacy_species_name}".'
        )

    def _extract_morphotype(self, scientific_name):
        if not scientific_name:
            return None

        name = scientific_name.strip()
        for morphotype in sorted(LEGACY_MORPHOTYPES, key=len, reverse=True):
            if name.endswith(morphotype):
                return morphotype

        return None

    def _legacy_condition_value(self, morphotype):
        if not morphotype:
            return None

        mapped = TAXA_MAP.get(morphotype) or {}
        return mapped.get('Zustand')

    def _build_temporal_payload(self, legacy_date):
        if not legacy_date:
            return None

        dt = datetime.combine(legacy_date, time.min).replace(tzinfo=dt_timezone.utc)
        timestamp = int(dt.timestamp() * 1000)

        return {
            'cron': {
                'type': 'timestamp',
                'format': 'unixtime',
                'timestamp': timestamp,
                'timezoneOffset': 0,
            },
            'type': 'Temporal',
        }

    def _build_point_feature(self, point_geojson):
        if not point_geojson:
            return None

        geometry = point_geojson
        if isinstance(point_geojson, str):
            try:
                geometry = json.loads(point_geojson)
            except json.JSONDecodeError:
                return None

        if not isinstance(geometry, dict):
            return None

        return {
            'type': 'Feature',
            'geometry': {
                'type': geometry.get('type'),
                'coordinates': geometry.get('coordinates'),
                'crs': {
                    'type': 'name',
                    'properties': {
                        'name': 'EPSG:4326',
                    },
                },
            },
            'properties': {
                'accuracy': 1,
            },
        }

    def _find_local_user_from_legacy_user_id(self, legacy_user_id):
        if legacy_user_id is None:
            return None

        user = LocalcosmosUser.objects.filter(
            legacy_user_info__provider='symfony',
            legacy_user_info__symfony__id=legacy_user_id,
        ).first()
        if user:
            return user

        return LocalcosmosUser.objects.filter(
            legacy_user_info__provider='symfony',
            legacy_user_info__symfony__id=str(legacy_user_id),
        ).first()

    def _create_or_get_dataset(self, app, observation_form, user, dataset_data, legacy_observation, commit=False):
        legacy_determination_id = legacy_observation['determination_id']
        existing = Dataset.objects.filter(
            app_uuid=app.uuid,
            data__legacyImport__determinationId=legacy_determination_id,
        ).first()

        if existing:
            return existing, False

        if not commit:
            return None, True

        with transaction.atomic():
            dataset = Dataset(
                app_uuid=app.uuid,
                observation_form=observation_form,
                data=dataset_data,
                created_at=datetime.now(tz=dt_timezone.utc),
                client_id=f'legacy-symfony-user-{legacy_observation.get("legacy_user_id")}',
                platform='legacy-import',
                user=None,
            )
            dataset.save()

            # Avoid triggering dataset-created points from Dataset.save() for migration data.
            Dataset.objects.filter(pk=dataset.pk).update(user=user)
            dataset.user = user

            return dataset, True

    def _create_user_points_for_observation(self, app, dataset, fallback_user, determination_points, commit=False):
        created_points = 0

        for legacy_point in determination_points:
            user = self._find_local_user_from_legacy_user_id(legacy_point.get('legacy_user_id'))
            if user is None:
                user = fallback_user

            if user is None:
                continue

            points = legacy_point.get('points')
            if points is None:
                continue

            description = legacy_point.get('description')
            awarded_for = AWARDED_FOR_MAPPING.get(description, description)

            already_exists = UserPoints.objects.filter(
                app=app,
                user=user,
                content_type__isnull=False,
                object_id=dataset.pk,
                points=points,
                awarded_for=awarded_for,
            ).exists()

            if already_exists:
                continue

            created_points += 1

            if commit:
                UserPoints.objects.award_user_points(
                    app=app,
                    user=user,
                    points=points,
                    awarded_for=awarded_for,
                    content_object=dataset,
                )

        return created_points

    def lookup_species_in_backbone_taxonomy(self, app, legacy_species_payload):
        
        errors = []
        
        app_features = app.get_features(app_state='review')
        
        review_app_path = app.get_installed_app_path('review')
        
        backbonetaxonomy = app_features['backbonetaxonomy']
        
        # search/taxon_latname
        alphabet_folder = backbonetaxonomy['search']['taxon_latname']
        
        start_letter = legacy_species_payload['sciencename'][0].upper()
        
        filename = f"{start_letter}.json"
        
        search_filepath = os.path.join(review_app_path, alphabet_folder, filename)
        
        
        try:
            with open(search_filepath, 'r', encoding='utf-8') as f:
                search_data = json.load(f)
        except Exception as exc:
            errors.append(f"Failed to load backbone taxonomy search file: {search_filepath}. Error: {exc}")
            self.stdout.write(self.style.ERROR(errors[-1]))
            return None
        
        # search for the species in the loaded search_data
        for entry in search_data:
            if entry['taxonLatname'].lower() == legacy_species_payload['sciencename'].lower():
                return {
                    'taxonSource': entry['taxonSource'],
                    'taxonNuid': entry['taxonNuid'],
                    'taxonLatname': entry['taxonLatname'],
                    'taxonAuthor': entry.get('taxonAuthor'),
                    'nameUuid': entry.get('nameUuid'),
                }

    def _get_legacy_db_config(self, options):
        config = {
            'host': options.get('legacy_host'),
            'port': options.get('legacy_port'),
            'dbname': options.get('legacy_name'),
            'user': options.get('legacy_user'),
            'password': options.get('legacy_password'),
            'sslmode': options.get('legacy_sslmode'),
        }

        missing = [key for key in ['host', 'port', 'dbname', 'user', 'password'] if not config.get(key)]
        if missing:
            missing_str = ', '.join(missing)
            raise CommandError(
                'Missing legacy DB connection settings: '
                f'{missing_str}. Provide --legacy-* arguments or LEGACY_DB_* env vars.'
            )

        return config

    def _connect_legacy_db(self, legacy_db_config):
        try:
            import psycopg2
        except ImportError as exc:
            raise CommandError(
                'psycopg2 is not installed in this environment.'
            ) from exc

        connect_kwargs = {
            'host': legacy_db_config['host'],
            'port': legacy_db_config['port'],
            'dbname': legacy_db_config['dbname'],
            'user': legacy_db_config['user'],
            'password': legacy_db_config['password'],
            'connect_timeout': 10,
        }

        if legacy_db_config.get('sslmode'):
            connect_kwargs['sslmode'] = legacy_db_config['sslmode']

        return psycopg2.connect(**connect_kwargs)


    def _fetch_symfony_observations(self, legacy_db_config, limit=None, only_legacy_user_id=None):
        where_clauses = ['d.deletedat IS NULL']
        params = []

        if only_legacy_user_id is not None:
            where_clauses.append('d.user_id = %s')
            params.append(only_legacy_user_id)

        where_sql = ' AND '.join(where_clauses)

        sql = (
            'SELECT '
            'd.id AS determination_id, '
            'd.user_id AS legacy_user_id, '
            'd.species_id AS legacy_species_id, '
            'd.amount, '
            'd.date AS observation_date, '
            'd.status AS legacy_status, '
            'd.type AS legacy_type, '
            'd.oldspeciesids, '
            'd.address, '
            'd.distance, '
            'ST_AsGeoJSON(d.point::geometry) AS point_geojson, '
            's.sciencename AS species_sciencename '
            'FROM be_determination d '
            'LEFT JOIN be_species s ON s.id = d.species_id '
            f'WHERE {where_sql} '
            'ORDER BY d.id ASC'
        )

        if limit is not None:
            sql += ' LIMIT %s'
            params.append(limit)

        try:
            with self._connect_legacy_db(legacy_db_config) as legacy_connection:
                with legacy_connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as exc:
            raise CommandError(
                'Could not read be_determination/be_species from legacy DB: '
                f"{exc}. If running in Docker Compose, use the legacy DB service name as --legacy-host."
            ) from exc

    def _fetch_symfony_determination_points(self, legacy_db_config, determination_ids):
        if not determination_ids:
            return defaultdict(list)

        placeholders = ', '.join(['%s'] * len(determination_ids))
        sql = (
            'SELECT '
            'id AS legacy_point_id, '
            'determination_id, '
            'user_id AS legacy_user_id, '
            'points, '
            'description '
            'FROM be_determination_point '
            f'WHERE determination_id IN ({placeholders}) '
            'ORDER BY id ASC'
        )

        grouped = defaultdict(list)

        try:
            with self._connect_legacy_db(legacy_db_config) as legacy_connection:
                with legacy_connection.cursor() as cursor:
                    cursor.execute(sql, determination_ids)
                    columns = [col[0] for col in cursor.description]
                    for row in cursor.fetchall():
                        payload = dict(zip(columns, row))
                        grouped[payload['determination_id']].append(payload)
        except Exception as exc:
            raise CommandError(
                'Could not read be_determination_point from legacy DB: '
                f"{exc}."
            ) from exc

        return grouped