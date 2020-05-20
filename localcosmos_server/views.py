from django.conf import settings
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from django.utils.http import is_safe_url
from django.http import Http404

from localcosmos_server.forms import EmailOrUsernameAuthenticationForm

# activate permission rules
from .permission_rules import *


class LogIn(LoginView):
    template_name = 'localcosmos_server/registration/login.html'
    form_class = EmailOrUsernameAuthenticationForm

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.GET.get(
            self.redirect_field_name,
            self.request.POST.get(self.redirect_field_name, '')
        )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''


class LoggedOut(TemplateView):
    template_name = 'localcosmos_server/registration/loggedout.html'


###################################################################################################################
#
#   LEGAL REQUIREMENTS
#
#   - in-app legal notice is built during build, available offline
#   - in-app privacy statement uses the api
#   - the views declared here are for links in emails
###################################################################################################################
from localcosmos_server.models import App
import os, json

class LegalNoticeMixin:
    
    def dispatch(self, request, *args, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])

        if not self.app.published_version_path:
            raise Http404('App not published yet')
    
        legal_notice_path = os.path.join(self.app.published_version_path, 'legal_notice.json')

        if not os.path.isfile(legal_notice_path):
            raise Http404('Legal notice not found')
            
        with open(legal_notice_path, 'r') as f:
            self.legal_notice = json.loads(f.read())

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app'] = self.app
        context['legal_notice'] = self.legal_notice
        return context
    

class LegalNotice(LegalNoticeMixin, TemplateView):

    template_name = 'localcosmos_server/legal/legal_notice.html'


class PrivacyStatement(LegalNoticeMixin, TemplateView):

    template_name = 'localcosmos_server/legal/privacy_statement.html'
