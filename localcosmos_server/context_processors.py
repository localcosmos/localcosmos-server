from django.conf import settings


def localcosmos_server(request):

    localcosmos_private = settings.LOCALCOSMOS_PRIVATE
    
    context = {
        'localcosmos_private' : localcosmos_private,
    }
    return context
    
    
    
