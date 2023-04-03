from django.conf import settings
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from datetime import datetime, timezone, timedelta


def get_domain_name(request):
    setup_domain_name = request.get_host().split(request.get_port())[0].split(':')[0]
    return setup_domain_name


def timestamp_from_utc_with_offset(utc_milliseconds, offset):

    delta_minutes = 0-offset

    tz = timezone(
        timedelta(minutes=delta_minutes)
    )

    # fromtimestamp takes seconds
    local = (utc_milliseconds / 1000) + (delta_minutes * 60)

    timestamp = datetime.fromtimestamp(local, tz=tz)

    return timestamp


def datetime_from_cron(cron):

    offset = cron['cron'].get('timezoneOffset', 0)

    utc = cron['cron']['timestamp']

    timestamp = timestamp_from_utc_with_offset(utc, offset)

    return timestamp

def api_filter_endpoints_hook(endpoints):
    # for (path, path_regex, method, callback) in endpoints:
    #      pass
    # drop html endpoints
    endpoints = [endpoint for endpoint in endpoints if not endpoint[0].endswith("{format}")]
    #exposed_endpoints = [endpoint for endpoint in endpoints if re.match(
    #    '/api/(user|password|template-content|token)/', endpoint[0])]

    return endpoints


def get_taxon_search_url(app, content=None):

    if settings.LOCALCOSMOS_PRIVATE == False: # and content and content.__class__.__name__ == 'TemplateContent':
        taxon_search_url = '/app-kit/searchtaxon/'
    else:
        taxon_search_url = reverse('search_app_taxon', kwargs={'app_uid':app.uid})

    return taxon_search_url


def get_public_schema_content_type_for_model(__class__):
    if 'django_tenants' in settings.INSTALLED_APPS:
        from django_tenants.utils import schema_context
        with schema_context('public'):
            content_type = ContentType.objects.get_for_model(__class__)
    
    else:
        content_type = ContentType.objects.get_for_model(__class__)

    return content_type


def get_public_schema_content_type(content_type_id):
    
    if 'django_tenants' in settings.INSTALLED_APPS:
        from django_tenants.utils import schema_context
        with schema_context('public'):
            content_type = ContentType.objects.get(pk=content_type_id)
    
    else:
        content_type = ContentType.objects.get(pk=content_type_id)

    return content_type