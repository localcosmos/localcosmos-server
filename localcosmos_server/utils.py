from django.conf import settings
from django.urls import reverse

import re


def get_domain_name(request):
    setup_domain_name = request.get_host().split(request.get_port())[0].split(':')[0]
    return setup_domain_name

from datetime import datetime, timezone, timedelta
def datetime_from_cron(cron):
    # fromtimestamp takes seconds

    delta_minutes = 0 - cron['cron'].get('timezone_offset', 0)
    
    tz = timezone(
        timedelta(minutes=delta_minutes)
    )

    utc = cron['cron']['timestamp']/1000

    local = utc + (delta_minutes * 60)

    timestamp = datetime.fromtimestamp(local, tz=tz)

    return timestamp

def api_filter_endpoints_hook(endpoints):
    # for (path, path_regex, method, callback) in endpoints:
    #      pass
    # drop html endpoints
    endpoints = [endpoint for endpoint in endpoints if not endpoint[0].endswith("{format}")]
    exposed_endpoints = [endpoint for endpoint in endpoints if re.match('/api/(user|app|password|online-content|token)/', endpoint[0])]

    return exposed_endpoints


def get_taxon_search_url(app, content=None):

    if settings.LOCALCOSMOS_PRIVATE == False and content and content.__class__.__name__ == 'TemplateContent':
        taxon_search_url = '/app-kit/searchtaxon/'
    else:
        taxon_search_url = reverse('search_app_taxon', kwargs={'app_uid':app.uid})

    return taxon_search_url