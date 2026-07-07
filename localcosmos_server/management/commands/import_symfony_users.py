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
        parser.add_argument(
            '--run-id',
            default=None,
            help=(
                'Optional identifier for a real import run. If omitted in --commit mode, '
                'a timestamp-based run id is generated and printed.'
            ),
        )
        parser.add_argument(
            '--list-not-migrated',
            action='store_true',
            help=(
                'List Localcosmos users imported from Symfony whose password/auth migration '
                'status is not django_password_migrated. This is a read-only report.'
            ),
        )
        parser.add_argument(
            '--list-not-imported-by-run',
            default=None,
            help=(
                'List legacy pd_user rows that were not imported/updated by the given run id. '
                'Requires legacy DB connection settings.'
            ),
        )
        parser.add_argument(
            '--list-missing-in-target',
            action='store_true',
            help=(
                'List legacy pd_user rows that are not present in LocalcosmosUser. '
                'Match is done by legacy symfony id first, then by username/email.'
            ),
        )

    def handle(self, *args, **options):
        user_model = get_user_model()

        if options['list_not_migrated']:
            self._report_not_migrated_users(user_model)
            return

        if options['list_not_imported_by_run']:
            legacy_db_config = self._get_legacy_db_config(options)
            self._report_not_imported_by_run(
                user_model=user_model,
                legacy_db_config=legacy_db_config,
                run_id=options['list_not_imported_by_run'],
                limit=options['limit'],
                only_user_id=options['only_user_id'],
            )
            return

        if options['list_missing_in_target']:
            legacy_db_config = self._get_legacy_db_config(options)
            self._report_missing_in_target(
                user_model=user_model,
                legacy_db_config=legacy_db_config,
                limit=options['limit'],
                only_user_id=options['only_user_id'],
            )
            return

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
        run_id = options.get('run_id')
        if commit and not run_id:
            run_id = timezone.now().strftime('%Y%m%dT%H%M%S%fZ')

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped_conflict': 0,
            'skipped_invalid': 0,
            'errors': 0,
        }
        conflict_details = []

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(
            f"Using legacy DB source {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )
        self.stdout.write(f'Starting import_symfony_users in {mode} mode for {len(rows)} rows.')
        if commit:
            self.stdout.write(f'Run id: {run_id}')

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

            legacy_info = self._build_legacy_user_info(row, run_id=run_id)

            existing_by_username = user_model.objects.filter(username=username).first()
            existing_by_email = user_model.objects.filter(email=email).first()
            existing_user = existing_by_username or existing_by_email

            try:
                if existing_user:
                    if not update_existing:
                        stats['skipped_conflict'] += 1
                        conflict_details.append(
                            {
                                'pd_user_id': row['id'],
                                'username': username,
                                'email': email,
                                'existing_by_username_pk': (
                                    existing_by_username.pk if existing_by_username else None
                                ),
                                'existing_by_email_pk': (
                                    existing_by_email.pk if existing_by_email else None
                                ),
                            }
                        )

                        conflict_reasons = []
                        if existing_by_username:
                            conflict_reasons.append(
                                f"username -> existing pk={existing_by_username.pk}"
                            )
                        if existing_by_email:
                            conflict_reasons.append(
                                f"email -> existing pk={existing_by_email.pk}"
                            )
                        reason_text = '; '.join(conflict_reasons) if conflict_reasons else 'unknown'

                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping pd_user id={row['id']}: user exists "
                                f"(username={username}, email={email}; {reason_text})"
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

        if conflict_details:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Conflict details:'))
            for conflict in conflict_details:
                self.stdout.write(
                    '  pd_user id={pd_user_id}, username={username}, email={email}, '
                    'existing_by_username_pk={existing_by_username_pk}, '
                    'existing_by_email_pk={existing_by_email_pk}'.format(**conflict)
                )

        if not commit:
            self.stdout.write(
                self.style.WARNING('Dry-run only. Re-run with --commit to persist changes.')
            )

    def _report_not_imported_by_run(self, user_model, legacy_db_config, run_id, limit=None, only_user_id=None):
        rows = self._fetch_symfony_users(
            legacy_db_config=legacy_db_config,
            limit=limit,
            only_user_id=only_user_id,
        )

        users_in_run = user_model.objects.filter(
            legacy_user_info__provider='symfony',
            legacy_user_info__import_run_id=run_id,
        )

        imported_legacy_ids = set()
        for user in users_in_run:
            legacy_info = user.legacy_user_info or {}
            symfony_info = legacy_info.get('symfony') or {}
            legacy_id = symfony_info.get('id')
            if legacy_id is not None:
                imported_legacy_ids.add(legacy_id)

        not_imported_rows = [
            row for row in rows
            if row.get('id') not in imported_legacy_ids
        ]

        self.stdout.write(
            f'Legacy users not imported by run_id={run_id}: {len(not_imported_rows)} '
            f'(out of {len(rows)} checked pd_user rows)'
        )

        if not not_imported_rows:
            return

        for row in not_imported_rows:
            username = (row.get('username') or '').strip()
            email = (row.get('email') or '').strip()

            reason = 'not imported in that run'
            if not username or not email:
                reason = 'missing username/email in legacy row'
            else:
                existing_by_username = user_model.objects.filter(username=username).first()
                existing_by_email = user_model.objects.filter(email=email).first()
                if existing_by_username or existing_by_email:
                    reason = 'conflict with existing Localcosmos user'

            self.stdout.write(
                f"- pd_user id={row.get('id')}, username={username}, email={email}, reason={reason}"
            )

    def _report_not_migrated_users(self, user_model):
        users = user_model.objects.filter(
            legacy_user_info__provider='symfony',
            legacy_user_info__auth_migration__isnull=False,
        ).exclude(
            legacy_user_info__auth_migration__status='django_password_migrated'
        ).order_by('pk')

        total = users.count()
        self.stdout.write(
            'Users with pending/unfinished password migration '
            f'(provider=symfony): {total}'
        )

        if total == 0:
            return

        for user in users:
            legacy_info = user.legacy_user_info or {}
            auth_migration = legacy_info.get('auth_migration') or {}
            symfony_info = legacy_info.get('symfony') or {}

            status = auth_migration.get('status') or 'unknown'
            failed_attempts = auth_migration.get('failed_legacy_login_attempts')
            last_failed = auth_migration.get('last_failed_legacy_login_at')
            password_migrated_at = auth_migration.get('password_migrated_at')
            legacy_id = symfony_info.get('id')

            self.stdout.write(
                f'- pk={user.pk}, username={user.username}, email={user.email}, '
                f'legacy_id={legacy_id}, status={status}, '
                f'failed_legacy_login_attempts={failed_attempts}, '
                f'last_failed_legacy_login_at={last_failed}, '
                f'password_migrated_at={password_migrated_at}'
            )

    def _report_missing_in_target(self, user_model, legacy_db_config, limit=None, only_user_id=None):
        rows = self._fetch_symfony_users(
            legacy_db_config=legacy_db_config,
            limit=limit,
            only_user_id=only_user_id,
        )

        missing_rows = []

        for row in rows:
            legacy_id = row.get('id')
            username = (row.get('username') or '').strip()
            email = (row.get('email') or '').strip()

            found_by_legacy_id = user_model.objects.filter(
                legacy_user_info__provider='symfony',
                legacy_user_info__symfony__id=legacy_id,
            ).exists()

            if found_by_legacy_id:
                continue

            found_by_username = bool(username) and user_model.objects.filter(username=username).exists()
            found_by_email = bool(email) and user_model.objects.filter(email=email).exists()

            if found_by_username or found_by_email:
                continue

            missing_rows.append(
                {
                    'id': legacy_id,
                    'username': username,
                    'email': email,
                }
            )

        self.stdout.write(
            f'Legacy users missing in target DB: {len(missing_rows)} '
            f'(out of {len(rows)} checked pd_user rows)'
        )

        if not missing_rows:
            return

        for row in missing_rows:
            self.stdout.write(
                f"- pd_user id={row.get('id')}, username={row.get('username')}, email={row.get('email')}"
            )

    def _apply_user_fields(self, user, row, legacy_info):
        user.first_name = row.get('firstname') or ''
        user.last_name = row.get('lastname') or ''

        user.legacy_user_info = legacy_info

    def _build_legacy_user_info(self, row, run_id=None):
        return {
            'source': 'beachexplorer',
            'provider': 'symfony',
            'scheme': 'unknown',
            'imported_at': timezone.now().isoformat(),
            'import_run_id': run_id,
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
