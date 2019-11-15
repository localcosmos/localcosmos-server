from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView

from localcosmos_server.forms import EmailOrUsernameAuthenticationForm

from .models import App

# activate permission rules
from .permission_rules import *

'''
    ServerConfig
    - displays the config of the server
    - displays installed Apps
'''
class ServerConfig(TemplateView):
    template_name = 'localcosmos_server/setup/server_config.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['installed_apps'] = App.objects.all()
        return context


class LogIn(LoginView):
    template_name = 'localcosmos_server/registration/login.html'
    form_class = EmailOrUsernameAuthenticationForm


class LoggedOut(TemplateView):
    template_name = 'localcosmos_server/registration/loggedout.html'


