# add self.online_content
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

        self.app_disk_path = self.app.get_installed_app_path(app_state='published')
        if not self.app_disk_path:
            return redirect(reverse('app_not_installed'))
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app' : self.app,
        })
        return context

        
