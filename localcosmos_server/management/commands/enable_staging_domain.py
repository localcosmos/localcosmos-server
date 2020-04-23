from django.core.management.base import BaseCommand, CommandError
from django.contrib.sites.models import Site

from localcosmos_server.models import App


'''
    create an app in the languages english, german and japanese (testing characters)
'''
class Command(BaseCommand):
    
    help = 'Fix Staging domain name'

    def handle(self, *args, **options):

        site = Site.objects.all().first()

        if 'staging' not in site.domain:

            staging_domain = 'staging.{0}'.format(site.domain)

            for app in App.objects.all():
                app.url = app.url.replace(site.domain, staging_domain)
                app.save()

            site.domain = staging_domain
            site.save()

        self.stdout.write('Finished fixing all domains.')
