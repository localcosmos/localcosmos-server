from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.contrib.auth.views import LoginView
from django.utils.http import is_safe_url
from django.http import Http404

from localcosmos_server.forms import EmailOrUsernameAuthenticationForm, ManageContentImageForm
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.models import ServerContentImage

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


from .view_mixins import ContentImageViewMixin
class ManageContentImageBase:
    
    form_class = ManageContentImageForm
    template_name = 'localcosmos_server/ajax/server_content_image_form.html'

    def dispatch(self, request, *args, **kwargs):

        self.new = False
        
        self.set_content_image(*args, **kwargs)
        if self.content_image:
            self.set_licence_registry_entry(self.content_image.image_store, 'source_image')
        else:
            self.licence_registry_entry = None
        self.set_taxon(request)
        
        return super().dispatch(request, *args, **kwargs)


    def form_valid(self, form):

        self.save_image(form)

        context = self.get_context_data(**self.kwargs)
        context['form'] = form

        return self.render_to_response(context)


class ManageServerContentImage(ContentImageViewMixin, ManageContentImageBase, FormView):
    pass


class DeleteServerContentImage(AjaxDeleteView):
    
    template_name = 'app_kit/ajax/delete_content_image.html'
    model = ServerContentImage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['image_type'] = self.object.image_type
        context['content_instance'] = self.object.content
        return context