from django.test import TestCase
from django.contrib.auth import get_user_model

from localcosmos_server.tests.mixins import (WithObservationForm, WithApp, WithUser)

from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command

from localcosmos_server.datasets.models import ObservationForm, Dataset

from localcosmos_server.models import App

from localcosmos_server.management.commands.create_test_datasets import DATASET_COUNT
from localcosmos_server.management.commands.import_symfony_users import Command as ImportSymfonyUsersCommand

class TestCreateTestData(WithObservationForm, WithApp, WithUser, TestCase):

    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "create_test_datasets",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_command(self):

        of_qry = ObservationForm.objects.all()
        ds_qry = Dataset.objects.all()

        self.assertFalse(of_qry.exists())
        self.assertFalse(ds_qry.exists())

        out = self.call_command()

        self.assertTrue(of_qry.exists())
        self.assertTrue(ds_qry.exists())

        app_count = App.objects.all().count()
        of_count = of_qry.count()

        self.assertEqual(ds_qry.count(), app_count * of_count * DATASET_COUNT)

        for ds in ds_qry:
            self.assertTrue(ds.taxon_latname is not None)
            #print(ds.taxon_latname)


# ---------------------------------------------------------------------------
# Helpers shared by ImportSymfonyUsers tests
# ---------------------------------------------------------------------------

LEGACY_DB_CONFIG = {
    'host': 'legacy-db',
    'port': 5432,
    'dbname': 'legacydb',
    'user': 'legacyuser',
    'password': 'legacypass',
    'sslmode': None,
}

def _make_pd_user_row(symfony_id=1, username='symfonyuser', email='symfony@example.com'):
    return {
        'id': symfony_id,
        'username': username,
        'email': email,
        'firstname': 'Sym',
        'lastname': 'Fony',
        'salt': 'salted',
        'password': 'hashed',
        'createdat': None,
        'birthday': None,
    }


class TestImportSymfonyUsersConflictAnnotation(WithUser, TestCase):
    """
    Tests for _annotate_conflict_on_existing_user and the conflict branch in handle().
    Legacy DB calls are patched out so no real Postgres connection is needed.
    """

    def setUp(self):
        super().setUp()
        self.user_model = get_user_model()
        self.existing_user = self.create_user()
        self.cmd = ImportSymfonyUsersCommand()
        self.cmd.stdout = MagicMock()
        self.cmd.style = MagicMock(
            WARNING=lambda s: s,
            SUCCESS=lambda s: s,
            ERROR=lambda s: s,
        )

    # ------------------------------------------------------------------
    # _annotate_conflict_on_existing_user unit tests
    # ------------------------------------------------------------------

    def test_annotate_sets_symfony_id_when_absent(self):
        row = _make_pd_user_row(symfony_id=42)
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user,
            row=row,
            match_reason='email',
            run_id='run-001',
        )
        self.existing_user.refresh_from_db()
        info = self.existing_user.legacy_user_info
        self.assertEqual(info['symfony']['id'], 42)

    def test_annotate_adds_conflict_entry(self):
        row = _make_pd_user_row(symfony_id=42)
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user,
            row=row,
            match_reason='email',
            run_id='run-001',
        )
        self.existing_user.refresh_from_db()
        conflicts = self.existing_user.legacy_user_info['symfony_import_conflicts']
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['symfony_id'], 42)
        self.assertEqual(conflicts[0]['match_reason'], 'email')
        self.assertEqual(conflicts[0]['import_run_id'], 'run-001')

    def test_annotate_accumulates_on_repeated_calls(self):
        row1 = _make_pd_user_row(symfony_id=10, username='u1', email='u1@example.com')
        row2 = _make_pd_user_row(symfony_id=11, username='u2', email='u2@example.com')
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user, row=row1, match_reason='email', run_id='r1'
        )
        self.existing_user.refresh_from_db()
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user, row=row2, match_reason='username', run_id='r2'
        )
        self.existing_user.refresh_from_db()
        conflicts = self.existing_user.legacy_user_info['symfony_import_conflicts']
        self.assertEqual(len(conflicts), 2)
        self.assertEqual(conflicts[0]['symfony_id'], 10)
        self.assertEqual(conflicts[1]['symfony_id'], 11)

    def test_annotate_preserves_existing_symfony_id_when_different(self):
        # Existing user was already imported as Symfony ID 99
        self.existing_user.legacy_user_info = {'symfony': {'id': 99}}
        self.existing_user.save()

        row = _make_pd_user_row(symfony_id=42)
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user,
            row=row,
            match_reason='email',
            run_id='run-002',
        )
        self.existing_user.refresh_from_db()
        info = self.existing_user.legacy_user_info
        # Primary ID unchanged
        self.assertEqual(info['symfony']['id'], 99)
        # Conflict still recorded in the list
        self.assertEqual(info['symfony_import_conflicts'][0]['symfony_id'], 42)

    def test_annotate_does_not_duplicate_symfony_id_when_same(self):
        # Same Symfony ID annotated twice (idempotency for the id field)
        row = _make_pd_user_row(symfony_id=42)
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user, row=row, match_reason='email', run_id='r1'
        )
        self.existing_user.refresh_from_db()
        self.cmd._annotate_conflict_on_existing_user(
            existing_user=self.existing_user, row=row, match_reason='email', run_id='r2'
        )
        self.existing_user.refresh_from_db()
        # symfony.id should still be 42 (set on first call, not cleared on second)
        self.assertEqual(self.existing_user.legacy_user_info['symfony']['id'], 42)

    # ------------------------------------------------------------------
    # handle() integration: conflict branch
    # ------------------------------------------------------------------

    def _run_handle(self, rows, commit=True, update_existing=False, run_id='test-run'):
        with patch.object(
            ImportSymfonyUsersCommand, '_fetch_symfony_users', return_value=rows
        ), patch.object(
            ImportSymfonyUsersCommand, '_get_legacy_db_config', return_value=LEGACY_DB_CONFIG
        ):
            out = StringIO()
            kwargs = {
                'commit': commit,
                'dry_run': False,
                'update_existing': update_existing,
                'run_id': run_id,
                'limit': None,
                'only_user_id': None,
                'list_not_migrated': False,
                'list_not_imported_by_run': None,
                'list_missing_in_target': False,
                'legacy_host': LEGACY_DB_CONFIG['host'],
                'legacy_port': LEGACY_DB_CONFIG['port'],
                'legacy_name': LEGACY_DB_CONFIG['dbname'],
                'legacy_user': LEGACY_DB_CONFIG['user'],
                'legacy_password': LEGACY_DB_CONFIG['password'],
                'legacy_sslmode': None,
            }
            call_command('import_symfony_users', stdout=out, stderr=StringIO(), **kwargs)
            return out.getvalue()

    def test_conflict_commit_annotates_existing_user(self):
        """Commit mode: existing user by email gets symfony.id and conflict entry."""
        row = _make_pd_user_row(
            symfony_id=77,
            username='brandnewname',
            email=self.test_email,  # same email as self.existing_user
        )
        self._run_handle([row], commit=True)

        self.existing_user.refresh_from_db()
        info = self.existing_user.legacy_user_info
        self.assertIsNotNone(info)
        self.assertEqual(info['symfony']['id'], 77)
        self.assertEqual(len(info['symfony_import_conflicts']), 1)
        self.assertEqual(info['symfony_import_conflicts'][0]['match_reason'], 'email')

    def test_conflict_dryrun_does_not_annotate_existing_user(self):
        """Dry-run mode: existing user must not be modified."""
        original_info = self.existing_user.legacy_user_info  # None initially

        row = _make_pd_user_row(
            symfony_id=77,
            username='brandnewname',
            email=self.test_email,
        )
        with patch.object(
            ImportSymfonyUsersCommand, '_fetch_symfony_users', return_value=[row]
        ), patch.object(
            ImportSymfonyUsersCommand, '_get_legacy_db_config', return_value=LEGACY_DB_CONFIG
        ):
            out = StringIO()
            kwargs = {
                'commit': False,
                'dry_run': False,
                'update_existing': False,
                'run_id': 'dry-run',
                'limit': None,
                'only_user_id': None,
                'list_not_migrated': False,
                'list_not_imported_by_run': None,
                'list_missing_in_target': False,
                'legacy_host': LEGACY_DB_CONFIG['host'],
                'legacy_port': LEGACY_DB_CONFIG['port'],
                'legacy_name': LEGACY_DB_CONFIG['dbname'],
                'legacy_user': LEGACY_DB_CONFIG['user'],
                'legacy_password': LEGACY_DB_CONFIG['password'],
                'legacy_sslmode': None,
            }
            call_command('import_symfony_users', stdout=out, stderr=StringIO(), **kwargs)

        self.existing_user.refresh_from_db()
        self.assertEqual(self.existing_user.legacy_user_info, original_info)

    def test_conflict_by_username_records_match_reason(self):
        """When conflict is on username, match_reason should be 'username'."""
        row = _make_pd_user_row(
            symfony_id=88,
            username=self.test_username,  # same username as self.existing_user
            email='different@example.com',
        )
        self._run_handle([row], commit=True)

        self.existing_user.refresh_from_db()
        info = self.existing_user.legacy_user_info
        self.assertEqual(info['symfony_import_conflicts'][0]['match_reason'], 'username')

    def test_dataset_lookup_works_after_conflict_annotation(self):
        """
        After annotation, the existing user is findable by symfony id using
        the same query a dataset importer would use.
        """
        row = _make_pd_user_row(symfony_id=55, email=self.test_email)
        self._run_handle([row], commit=True)

        found = self.user_model.objects.filter(
            legacy_user_info__symfony__id=55
        ).first()
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.existing_user.pk)

