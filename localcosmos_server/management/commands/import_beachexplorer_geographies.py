import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry

from localcosmos_server.models import App
from localcosmos_server.geography.models import PolygonCategory, GeographyPolygon


class Command(BaseCommand):
    help = 'Import geographies from Symfony legacy database (stub).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of legacy geography rows to process.',
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Reserved for the future import implementation.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without writing changes. This is the default stub behavior.',
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

        legacy_db_config = self._get_legacy_db_config(options)

        self.stdout.write(
            f"Using legacy DB source {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )
        self.stdout.write(
            f"Starting import_beachexplorer_geographies in {'COMMIT' if commit else 'DRY-RUN'} mode."
        )

        geographies = self._fetch_symfony_geographies(
            legacy_db_config=legacy_db_config,
            limit=options['limit'],
        )

        self.stdout.write(f'Legacy geography rows found: {len(geographies)}')

        stats = self._import_geographies(geographies=geographies, commit=commit)

        self.stdout.write('')
        self.stdout.write('Import summary:')
        for key, value in stats.items():
            self.stdout.write(f'  {key}: {value}')

        if not commit:
            self.stdout.write(
                self.style.WARNING('Dry-run only. Re-run with --commit to persist changes.')
            )

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

    def _fetch_symfony_geographies(self, legacy_db_config, limit=None):
        sql = (
            'SELECT '
            'id, '
            'name, '
            'district, '
            'ST_AsText(polygon::geometry) AS geometry_wkt '
            'FROM be_polygon '
            'WHERE polygon IS NOT NULL '
            'AND deletedat IS NULL '
            'ORDER BY id ASC'
        )

        params = []
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
                'Could not read be_polygon from legacy DB: '
                f"{exc}. If running in Docker Compose, use the legacy DB service name as --legacy-host."
            ) from exc

    def _import_geographies(self, geographies, commit=False):
        app = App.objects.get(name='BeachExplorer')

        polygon_category_name = 'Raster BeachExplorer'
        polygon_category, _ = PolygonCategory.objects.get_or_create(
            name=polygon_category_name,
            app=app
        )

        stats = {
            'processed': 0,
            'created': 0,
            'skipped_existing': 0,
            'skipped_invalid': 0,
            'errors': 0,
        }

        for row in geographies:
            stats['processed'] += 1

            legacy_id = row.get('id')
            name = (row.get('name') or row.get('district') or '').strip()
            geometry_wkt = row.get('geometry_wkt')

            if not name or not geometry_wkt:
                stats['skipped_invalid'] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping be_polygon id={legacy_id}: missing name or geometry.'
                    )
                )
                continue

            try:
                geometry = GEOSGeometry(geometry_wkt, srid=4326)
                geometry.transform(3857)

                existing = GeographyPolygon.objects.filter(
                    app=app,
                    category=polygon_category,
                    name=name,
                    geometry=geometry,
                ).first()

                if existing:
                    stats['skipped_existing'] += 1
                    continue

                stats['created'] += 1

                if commit:
                    GeographyPolygon.objects.create(
                        app=app,
                        category=polygon_category,
                        name=name,
                        geometry=geometry,
                    )

            except Exception as exc:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed be_polygon id={legacy_id}: {exc}'
                    )
                )

        return stats