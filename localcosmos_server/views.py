from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.contrib.auth.views import LoginView
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import Http404
from django.urls import reverse

from localcosmos_server.forms import EmailOrUsernameAuthenticationForm, ManageContentImageForm
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.models import ServerContentImage
from localcosmos_server.view_mixins import AppMixin

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
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''


class LoggedOut(TemplateView):
    template_name = 'localcosmos_server/registration/loggedout.html'


###################################################################################################################
#
#   APP SPECIFIC PASSWORD RESET
#
#   - visually app-specific, therfore, the app uid hast to be in the url
#   - all app admin pages require a login, so /server/ is the place to do this
###################################################################################################################
from django.contrib.auth.views import (PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView,
    PasswordResetDoneView)


class AppBaseTemplateMixin:
    extra_context = {'base_template': 'localcosmos_server/app/base.html'}


class AppPasswordResetView(AppMixin, AppBaseTemplateMixin, PasswordResetView):
    template_name = 'localcosmos_server/registration/password_reset_form.html'
    email_template_name='localcosmos_server/app/registration/password_reset_email.html'

    def get_success_url(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }
        success_url = reverse('app_password_reset_done', kwargs=url_kwargs)
        return success_url

    def form_valid(self, form):
        self.extra_email_context = {
            'app': self.app,
        }

        return super().form_valid(form)


class AppPasswordResetConfirmView(AppMixin, AppBaseTemplateMixin, PasswordResetConfirmView):
    template_name='localcosmos_server/registration/password_reset_confirm.html'

    def get_success_url(self):
        url_kwargs = {
            'app_uid': self.app.uid,
        }
        success_url = reverse('app_password_reset_complete', kwargs=url_kwargs)
        return success_url


# confirmation that the password has been changed
class AppPasswordResetCompleteView(AppMixin, AppBaseTemplateMixin, PasswordResetCompleteView):
    template_name='localcosmos_server/app/registration/password_reset_complete.html'

# confimration that the email has been sent
class AppPasswordResetDoneView(AppMixin, AppBaseTemplateMixin, PasswordResetDoneView):
    template_name='localcosmos_server/registration/password_reset_done.html'


###################################################################################################################
#
#   LEGAL REQUIREMENTS
#
#   - in-app legal notice is built during build, available offline
#   - in-app privacy statement uses the api
#   - the views declared here are for links in emails
###################################################################################################################
from localcosmos_server.models import App

class LegalTextMixin:
    
    def dispatch(self, request, *args, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        self.legal_text = self.app.get_legal_frontend_text(self.text_key)
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app'] = self.app
        context['legal_text'] = self.legal_text
        return context
    

class LegalNotice(LegalTextMixin, TemplateView):

    text_key = 'legalNotice'

    template_name = 'localcosmos_server/legal/legal_notice.html'


class PrivacyStatement(LegalTextMixin, TemplateView):

    text_key = 'privacyPolicy'

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