# add self.online_content
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from localcosmos_server.models import App

'''
    OnlineContent is available only for installed apps
'''

class OnlineContentMixin:

    def dispatch(self, request, *args, **kwargs):
        if hasattr(request, 'app') and request.app != None:
            self.app = request.app
        else:
            self.app = App.objects.get(uid=kwargs['app_uid'])

        if settings.LOCALCOSMOS_OPEN_SOURCE == True:
            app_state = 'published'
        else:
            app_state = 'preview'
        
        self.app_disk_path = self.app.get_installed_app_path(app_state=app_state)
        
        if not self.app_disk_path:
            raise FileNotFoundError('[{0}] self.app_disk_path for app_state: {1} is {2}'.format(self.app.uid,
                                                                    app_state, self.app_disk_path))
        
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app' : self.app,
        })
        return context

        
