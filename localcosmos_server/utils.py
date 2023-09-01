from django.conf import settings
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from datetime import datetime, timezone, timedelta


def get_domain_name(request):
    setup_domain_name = request.get_host().split(request.get_port())[0].split(':')[0]
    return setup_domain_name


def timestamp_from_utc_with_offset(utc_milliseconds, offset_minutes):

    # the offset is expectes as given from javascript's .getTimezoneOffset
    # which returns the value you have to add to the local time to get back to UTC
    # the way from UTC to local time requires the opposite 
    delta_minutes = 0-offset_minutes

    tz = timezone(
        timedelta(minutes=delta_minutes)
    )

    # fromtimestamp takes seconds
    utc_seconds = int((utc_milliseconds / 1000))

    # fromtimestamp expects a POSIX timestamp, which is the number of seconds
    # since Thursday, 01.January 1970 UTC
    timestamp = datetime.fromtimestamp(utc_seconds, tz=tz)

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