from django.conf import settings


def localcosmos_server(request):

    localcosmos_private = settings.LOCALCOSMOS_PRIVATE
    fcm_enabled = getattr(settings, 'ENABLE_FIREBASE_MESSAGING', False)
    
    context = {
        'localcosmos_private' : localcosmos_private,
        'fcm_enabled' : fcm_enabled,
    }
    return context
    
    
    
