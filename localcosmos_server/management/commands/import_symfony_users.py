from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

import os


# Migration scope (draft):
# - Create or update LocalcosmosUser fields: username, email, first_name, last_name.
# - Store only these legacy Symfony fields in legacy_user_info:
#   id, salt, password, createdat, birthday.
# - Read legacy users from a dedicated PostgreSQL connection (legacy DB container
#   in the same Docker network), not from the default Django database.
# - Initialize auth migration states in legacy_user_info:
#   status values:
#     - legacy_pending_password_migration: imported, legacy password check still required.
#     - django_password_migrated: password rehashed to Django and legacy check can be skipped.
#     - legacy_locked_after_failures: too many failed legacy logins, require reset/support.
#   tracking fields:
#     - failed_legacy_login_attempts: counter for unsuccessful legacy login checks.
#     - last_failed_legacy_login_at: timestamp of last failed legacy login.
#     - password_migrated_at: timestamp when Django password migration completed.
# - Do not migrate Symfony passwords into Django's password field in this draft.


class Command(BaseCommand):
    help = 'Import users from Symfony pd_user into LocalcosmosUser (draft).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of pd_user rows to process.',
        )
        parser.add_argument(
            '--only-user-id',
            type=int,
            default=None,
            help='Only import a single pd_user.id.',
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Persist changes. Without this flag, the command runs in dry-run mode.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run checks and report collisions without writing any changes.',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update an existing user when username or email already exists.',
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
        user_model = get_user_model()

        if options['commit'] and options['dry_run']:
            raise CommandError('Use either --commit or --dry-run, not both.')

        legacy_db_config = self._get_legacy_db_config(options)

        rows = self._fetch_symfony_users(
            legacy_db_config=legacy_db_config,
            limit=options['limit'],
            only_user_id=options['only_user_id'],
        )

        if not rows:
            self.stdout.write(self.style.WARNING('No pd_user rows found.'))
            return

        # Default mode is dry-run unless --commit is provided.
        commit = options['commit'] and not options['dry_run']
        update_existing = options['update_existing']

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped_conflict': 0,
            'skipped_invalid': 0,
            'errors': 0,
        }

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(
            f"Using legacy DB source {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )
        self.stdout.write(f'Starting import_symfony_users in {mode} mode for {len(rows)} rows.')

        for row in rows:
            stats['processed'] += 1

            username = (row.get('username') or '').strip()
            email = (row.get('email') or '').strip()

            if not username or not email:
                stats['skipped_invalid'] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping pd_user id={row.get('id')}: missing username/email"
                    )
                )
                continue

            legacy_info = self._build_legacy_user_info(row)

            existing_by_username = user_model.objects.filter(username=username).first()
            existing_by_email = user_model.objects.filter(email=email).first()
            existing_user = existing_by_username or existing_by_email

            try:
                if existing_user:
                    if not update_existing:
                        stats['skipped_conflict'] += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping pd_user id={row['id']}: user exists "
                                f"(username={username}, email={email})"
                            )
                        )
                        continue

                    stats['updated'] += 1

                    if commit:
                        self._apply_user_fields(existing_user, row, legacy_info)
                        existing_user.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated user for pd_user id={row['id']} (pk={existing_user.pk})"
                        )
                    )
                    continue

                stats['created'] += 1

                if commit:
                    user = user_model.objects.create_user(username=username, email=email, password=None)
                    self._apply_user_fields(user, row, legacy_info)
                    user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created user for pd_user id={row['id']} (username={username})"
                    )
                )

            except Exception as exc:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f"Failed pd_user id={row['id']}: {exc}")
                )

        self.stdout.write('')
        self.stdout.write('Import summary:')
        for key, value in stats.items():
            self.stdout.write(f'  {key}: {value}')

        if not commit:
            self.stdout.write(
                self.style.WARNING('Dry-run only. Re-run with --commit to persist changes.')
            )

    def _apply_user_fields(self, user, row, legacy_info):
        user.first_name = row.get('firstname') or ''
        user.last_name = row.get('lastname') or ''

        user.legacy_user_info = legacy_info

    def _build_legacy_user_info(self, row):
        return {
            'source': 'beachexplorer',
            'provider': 'symfony',
            'scheme': 'unknown',
            'imported_at': timezone.now().isoformat(),
            'auth_migration': {
                'status': 'legacy_pending_password_migration',
                'failed_legacy_login_attempts': 0,
                'last_failed_legacy_login_at': None,
                'password_migrated_at': None,
            },
            'symfony': {
                'id': row.get('id'),
                'salt': row.get('salt'),
                'password': row.get('password'),
                'createdat': str(row.get('createdat')) if row.get('createdat') else None,
                'birthday': str(row.get('birthday')) if row.get('birthday') else None,
            },
            'import_command': 'import_symfony_users',
            'version': 1,
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

    def _fetch_symfony_users(self, legacy_db_config, limit=None, only_user_id=None):
        where_clauses = []
        params = []

        if only_user_id is not None:
            where_clauses.append('id = %s')
            params.append(only_user_id)

        where_sql = ''
        if where_clauses:
            where_sql = ' WHERE ' + ' AND '.join(where_clauses)

        sql = (
            'SELECT id, username, email, firstname, lastname, '
            'salt, password, createdat, birthday '
            'FROM pd_user'
            f'{where_sql} '
            'ORDER BY id ASC'
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
                'Could not read pd_user from legacy DB: '
                f"{exc}. If running in Docker Compose, use the legacy DB service name as --legacy-host."
            ) from exc
