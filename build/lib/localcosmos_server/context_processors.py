from django.conf import settings


def localcosmos_server(request):

    localcosmos_private = settings.LOCALCOSMOS_OPEN_SOURCE
    
    context = {
        'localcosmos_private' : localcosmos_private,
    }
    return context
    
    
    
