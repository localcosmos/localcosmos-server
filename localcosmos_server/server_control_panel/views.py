from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.http import Http404
from django.utils.translation import gettext as _

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from localcosmos_server.models import App, SecondaryAppLanguages
from localcosmos_server.generic_views import AjaxDeleteView

from localcosmos_server import __version__ as SERVER_VERSION

from .forms import InstallAppForm, EditAppForm

from urllib import request
from urllib.error import HTTPError, URLError

import json, os, shutil, zipfile

LOCALCOSMOS_PRIVATE = getattr(settings, 'LOCALCOSMOS_PRIVATE')

class LoginRequiredMixin:

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

'''
    Home
'''
class AppsContextMixin:
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['apps'] = App.objects.all()
        return context


class ServerControlPanelHome(LoginRequiredMixin, AppsContextMixin, TemplateView):
    
    template_name = 'server_control_panel/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['server_version'] = SERVER_VERSION
        return context


class LCPrivateOnlyMixin:
    
    def dispatch(self, request, *args, **kwargs):
        if LOCALCOSMOS_PRIVATE == False:
            raise Http404('The resource you requested is only available on LC Private installations')
        return super().dispatch(request, *args, **kwargs)


'''
    Install or Update App
    - only for LC Private installations
    - collect data and upload app .zip
    - also capable of updating an app
'''
class InstallApp(LoginRequiredMixin, LCPrivateOnlyMixin, FormView):
    template_name = 'server_control_panel/install_app.html'
    form_class = InstallAppForm

    def dispatch(self, request, *args, **kwargs):

        self.app = None
        
        app_uid = kwargs.get('app_uid', None)

        if app_uid:
            self.app = App.objects.get(uid=app_uid)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localcosmos_apps_root'] = settings.LOCALCOSMOS_APPS_ROOT
        context['success'] = False
        context['app'] = self.app
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.app != None:
            initial['url'] = self.app.url
        return initial

    def form_valid(self, form):

        context = self.get_context_data(**self.kwargs)

        errors = []

        # temporarily save the zipfile
        zip_file = form.cleaned_data['zipfile']

        temp_folder = os.path.join(settings.MEDIA_ROOT, 'apps/tmp')
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)

        if not os.path.isdir(temp_folder):
            os.makedirs(temp_folder)

        zip_filename = 'app.zip'
        zip_destination_path = os.path.join(temp_folder, zip_filename)
        
        with open(zip_destination_path, 'wb+') as zip_destination:
            for chunk in zip_file.chunks():
                zip_destination.write(chunk)

        # the zipfile is now stored on disk
        # unzip contents
        unzip_path = os.path.join(temp_folder, 'app')

        with zipfile.ZipFile(zip_destination_path, 'r') as zip_file:
            zip_file.extractall(unzip_path)

        try:
            settings_path = os.path.join(unzip_path, 'www', 'settings.json')

            with open(settings_path, 'r') as f:
                app_settings = json.loads(f.read())

            # read required parameters
            app_name = app_settings['NAME']
            app_uuid = app_settings['APP_UUID']
            app_uid = app_settings['APP_UID']
            app_version = app_settings['APP_VERSION']
            primary_language = app_settings['PRIMARY_LANGUAGE']
            languages = app_settings['LANGUAGES']
                
        except Exception as e:
            # could not import the zip
            # return an error
            error_message = _('Error importing the app. Please upload a valid app .zip file: {0}'.format(str(e)))
            errors.append(error_message)

        # [UPDATE only] check if package matches app
        if self.app is not None:
            if self.app.uid != app_uid or str(self.app.uuid) != app_uuid:
                error_message = _('The zip file you uploaded does not contain the app {0}'.format(self.app.name))
                errors.append(error_message)

        if not errors:
            
            app_folder = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, app_uid)
            
            # get or create app object
            app = App.objects.filter(uid=app_uid).first()
            
            if app:
                # update the url
                app.url = form.cleaned_data['url']
                app.save()

            else:

                # the app uuid has to be the same as in app_settings, alongside other parameters
                
                app_path = os.path.join(app_folder, 'www')
                url = form.cleaned_data['url']
                #cleaned_url = url.replace('https://', '').replace('http://', '')
                
                app = App(
                    uuid = app_uuid,
                    uid = app_uid,
                    name = app_name,
                    primary_language = primary_language,
                    published_version = app_version,
                    published_version_path = app_path,
                    url = url
                )
                
                app.save()

            # update languages
            existing_secondary_languages = list(SecondaryAppLanguages.objects.filter(app=app
                            ).values_list('language_code', flat=True))

            languages.remove(primary_language)

            # create secondary languages
            for language in languages:

                if language in existing_secondary_languages:
                    existing_secondary_languages.remove(language)

                else:

                    secondary_language = SecondaryAppLanguages(
                        app=app,
                        language_code=language,
                    )

                    secondary_language.save()

            # remove remaining existing_secondary_languages, which are the remove languages
            for language_code in existing_secondary_languages:
                remove_language = SecondaryAppLanguages.objects.filter(app=app, language_code=language_code).first()
                if remove_language:
                    remove_language.delete()

            # remove currently installed app and upload new one
            if os.path.isdir(app_folder):
                shutil.rmtree(app_folder)

            # copy unzipped folder into app dir
            shutil.copytree(unzip_path, app_folder)

        # remove the temp folder
        shutil.rmtree(temp_folder)
            
        context['errors'] = errors
        if not errors:
            context['success'] = True
        
        return self.render_to_response(context)


class UninstallApp(LoginRequiredMixin, AjaxDeleteView):
    
    model = App

    def get_deletion_message(self):
        return _('Do you really want to uninstall %s?' % self.object)

    def get(self, request, *args, **kwargs):
        if LOCALCOSMOS_PRIVATE == False:
            raise Http404('Not available on Local Cosmos commercial')

        return super().get(request, *args, **kwargs)



'''
    AppMixin and App specific views
'''
class AppMixin(AppsContextMixin):
    
    def dispatch(self, request, *args, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app'] = self.app
        return context



class EditApp(LoginRequiredMixin, AppMixin, FormView):

    form_class = EditAppForm
    template_name = 'server_control_panel/edit_app.html'

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['instance'] = self.app
        return form_kwargs

    def form_valid(self, form):

        app = form.save()

        context = self.get_context_data(**self.kwargs)
        context['app'] = app
        context['success'] = True

        return self.render_to_response(context)
    


class CheckAppApiStatus(LoginRequiredMixin, AppMixin, TemplateView):

    template_name = 'server_control_panel/app_api_status.html'

    def check_api_status(self):
        settings = self.app.get_settings(app_state='published')

        result = {
            'success' : True,
            'error' : None,
        }
        
        api_url = settings['API_URL']

        try:
            response = request.urlopen(api_url)
            json_response = json.loads(response.read())
            
        except HTTPError as e:
            result['error'] = e.code
            result['success'] = False

        except URLError as e:
            result['error'] = e.reason
            result['success'] = False
            
        except:
            result['success'] = False
            result['error'] = 'error'
        

        return result
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_check'] = self.check_api_status()
        return context

