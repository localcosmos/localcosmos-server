"""
Clean up taxon_latname in the backbone taxonomy:
  - "ABCD gen XYZ" -> "ABCD XYZ"
  - "ABCD spp." -> "ABCD spp"
"""
from django.db.models import Q
from django.core.management.base import BaseCommand

from app_kit.taxonomy.models import TaxonomyModelRouter

taxonomy_models = TaxonomyModelRouter('taxonomy.sources.custom')
CustomTaxonTree = taxonomy_models.TaxonTreeModel

REPLACEMENTS = [
    (' gen ', ' '),
    ('spp.', 'spp'),
]


class Command(BaseCommand):
    help = 'Remove " gen " and trailing dot from "spp." in backbone taxon_latname entries.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Persist changes (default: dry-run).',
        )

    def handle(self, *args, **options):
        commit = options['commit']

        filter_q = Q()
        for old, _ in REPLACEMENTS:
            filter_q |= Q(taxon_latname__contains=old)

        qs = CustomTaxonTree.objects.filter(filter_q)
        total = qs.count()

        self.stdout.write(f'Entries requiring fixes: {total}')
        self.stdout.write(f'Mode: {"COMMIT" if commit else "DRY-RUN"}')
        self.stdout.write('')

        fixed = 0

        for entry in qs.order_by('id'):
            old_name = entry.taxon_latname
            new_name = old_name
            for old, new in REPLACEMENTS:
                new_name = new_name.replace(old, new)

            self.stdout.write(
                f'  {"FIX " if commit else "WOULD FIX"}  '
                f'id={entry.id:>6}  {old_name!r} -> {new_name!r}'
            )

            if commit:
                entry.taxon_latname = new_name
                entry.save(update_fields=['taxon_latname'])

            fixed += 1

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'{"Fixed" if commit else "Would fix"} {fixed} of {total} entries.'
            )
        )
