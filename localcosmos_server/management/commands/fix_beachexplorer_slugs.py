"""
Fix CustomTaxonTree slugs that end with '-none'.

When taxon_author is None the slug is generated from '{taxon_latname} None',
which slugify() turns into '{taxon_latname}-none'.  This command finds every
affected entry and replaces the trailing '-none' with '-{entry.id}'.
"""
from django.core.management.base import BaseCommand

from app_kit.taxonomy.models import TaxonomyModelRouter

taxonomy_models = TaxonomyModelRouter('taxonomy.sources.custom')
CustomTaxonTree = taxonomy_models.TaxonTreeModel


class Command(BaseCommand):
    help = (
        'Fix CustomTaxonTree slugs that end with "-none" by replacing the '
        'suffix with "-<id>".'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Persist the slug fixes (default: dry-run).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without writing anything (default behaviour).',
        )

    def handle(self, *args, **options):
        commit = options['commit'] and not options['dry_run']

        qs = CustomTaxonTree.objects.filter(slug__endswith='-none')
        total = qs.count()

        self.stdout.write(f'Entries with slugs ending in "-none": {total}')
        self.stdout.write(f'Mode: {"COMMIT" if commit else "DRY-RUN"}')
        self.stdout.write('')

        fixed = 0
        skipped = 0

        for entry in qs.order_by('id'):
            old_slug = entry.slug
            # Strip the trailing '-none' and append '-<id>'
            new_slug = old_slug[: -len('-none')] + f'-{entry.id}'

            # Guard against the new slug colliding with an existing one
            conflict = (
                CustomTaxonTree.objects
                .filter(slug=new_slug)
                .exclude(pk=entry.pk)
                .exists()
            )
            if conflict:
                self.stdout.write(
                    self.style.WARNING(
                        f'  SKIP  id={entry.id:>6}  {old_slug!r} → {new_slug!r}  '
                        '(new slug already taken)'
                    )
                )
                skipped += 1
                continue

            self.stdout.write(
                f'  {"FIX " if commit else "WOULD FIX"}  '
                f'id={entry.id:>6}  {old_slug!r} → {new_slug!r}'
            )

            if commit:
                entry.slug = new_slug
                entry.save(update_fields=['slug'])

            fixed += 1

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. {"Fixed" if commit else "Would fix"}: {fixed}  |  Skipped (conflict): {skipped}'
            )
        )
