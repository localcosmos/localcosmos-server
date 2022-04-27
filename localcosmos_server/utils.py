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
