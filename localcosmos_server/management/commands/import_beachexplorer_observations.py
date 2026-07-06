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

from django.core.management.base import BaseCommand, CommandError

from localcosmos_server.models import LocalcosmosUser
from localcosmos_server.datasets import Dataset, ObservationForm

# a map for taxa that do not exist 1:1 in the new database. For example morphotypes, dead specimens, etc. 
TAXA_MAP = {
    '(eggs)' : {
        
    },
    '(t)' : {
        'Zustand': 'tot',
    }
}

LEGACY_MORPHOTYPES = [
    '(†)',
    '(13./14. Jh)', # probalby no morphotype
    '(15./18. Jh)', # probalby no morphotype
    '(17./18. Jh)', # probalby no morphotype
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



class Command(BaseCommand):
    help = 'Import observations from Symfony legacy database (stub).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of legacy observation rows to process.',
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

        legacy_db_config = self._get_legacy_db_config(options)

        self.stdout.write(
            f"Using legacy DB source {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )
        self.stdout.write('import_beachexplorer_observations is currently a stub.')
        self.stdout.write('Next step: add the legacy Symfony observation query and mapping logic.')

        observations = self._fetch_symfony_observations(
            legacy_db_config=legacy_db_config,
            limit=options['limit'],
        )

        self.stdout.write(f'Legacy observation rows found: {len(observations)}')

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


    def _fetch_symfony_observations(self, legacy_db_config, limit=None):
        
        # table be_determination contains observations
        # foreign key: species_id -> be_species.id
        
        # be_determination columns:
        #   - id
        #   - species_id
        #   - user_id
        #   - date
        #   - point
        #   - deletedat has to be NULL !
        #   - amount
        
        # table be_species
        # sciencename column
        
        
        raise NotImplementedError(
            'Observation import query is not implemented yet. '
            'Use this stub to wire the Symfony DB connection and then add the legacy observation mapping.'
        )