"""
Import BeachExplorer object classes into the LocalCosmos app kit.

Reads all object-class definitions from TAXA_MAP in beachexplorer_mapping.py
and creates the corresponding ObjectClass entries for the target app's
ObjectClasses feature.  Each (scientific_name, german_name) pair is taken
from the first TAXA_MAP entry that references it, so the command is safe to
re-run (existing entries are left unchanged).
"""
from django.core.management.base import BaseCommand, CommandError

from localcosmos_server.models import App

from app_kit.models import MetaApp
from app_kit.features.object_classes.models import ObjectClasses, ObjectClass

from .beachexplorer_mapping import OBJECT_CLASS_NAMES


class Command(BaseCommand):
    help = (
        'Import BeachExplorer object classes into the ObjectClasses feature '
        'of the target LocalCosmos app.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-name',
            default='BeachExplorer',
            help='LocalCosmos app name (or uid) that owns the ObjectClasses feature. '
                 'Default: BeachExplorer',
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Persist new ObjectClass entries.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without writing anything (default behaviour).',
        )

    def handle(self, *args, **options):
        if options['commit'] and options['dry_run']:
            raise CommandError('Use either --commit or --dry-run, not both.')

        commit = options['commit'] and not options['dry_run']

        # ── resolve app / meta_app ──────────────────────────────────────────
        app = self._get_target_app(options['app_name'])
        meta_app = MetaApp.objects.filter(app=app).first()
        if not meta_app:
            raise CommandError(
                f'No MetaApp found for app "{app.name}" (uid={app.uid}). '
                'Ensure the app is installed and has a MetaApp.'
            )

        # ── resolve ObjectClasses feature ───────────────────────────────────
        oc_link = meta_app.get_generic_content_links(ObjectClasses).first()
        if not oc_link:
            raise CommandError(
                f'No ObjectClasses feature found for MetaApp "{meta_app.name}". '
                'Add an ObjectClasses feature to the app first.'
            )
        object_classes_feature = oc_link.generic_content

        # ── collect definitions from OBJECT_CLASS_NAMES ────────────────────
        definitions = {
            k: v if v is not None else k
            for k, v in OBJECT_CLASS_NAMES.items()
        }

        self.stdout.write(
            f'Target app : {app.name} (uid={app.uid})'
        )
        self.stdout.write(
            f'ObjectClasses feature : {object_classes_feature} (pk={object_classes_feature.pk})'
        )
        self.stdout.write(
            f'Object classes found in TAXA_MAP : {len(definitions)}'
        )
        self.stdout.write(
            f'Mode : {"COMMIT" if commit else "DRY-RUN"}'
        )
        self.stdout.write('')

        stats = {'created': 0, 'existing': 0}

        for scientific_name, german_name in sorted(definitions.items()):
            exists = ObjectClass.objects.filter(
                object_classes=object_classes_feature,
                scientific_name=scientific_name,
            ).exists()

            if exists:
                stats['existing'] += 1
                self.stdout.write(
                    f'  SKIP  {scientific_name:<30}  already exists'
                )
                continue

            stats['created'] += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  {"CREATE" if commit else "WOULD CREATE"}  '
                    f'{scientific_name:<30}  name="{german_name}"'
                )
            )

            if commit:
                ObjectClass.objects.create(
                    object_classes=object_classes_feature,
                    name=german_name,
                    scientific_name=scientific_name,
                )

        self.stdout.write('')
        self.stdout.write(
            f'Done. created={stats["created"]}, already_existed={stats["existing"]}.'
        )

        if not commit:
            self.stdout.write(
                self.style.WARNING('Dry-run only — re-run with --commit to persist.')
            )

    # ── helpers ────────────────────────────────────────────────────────────

    def _get_target_app(self, app_name):
        for lookup in [
            {'name': app_name},
            {'name__iexact': app_name},
            {'uid': app_name},
        ]:
            app = App.objects.filter(**lookup).first()
            if app:
                return app
        raise CommandError(f'No App found with name/uid "{app_name}".')
