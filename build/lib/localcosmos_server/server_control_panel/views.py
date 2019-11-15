from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from localcosmos_server.models import App, SecondaryAppLanguages

from .forms import InstallAppForm

from urllib import request
from urllib.error import HTTPError, URLError

import json, os, shutil, zipfile

LOCALCOSMOS_OPEN_SOURCE = getattr(settings, 'LOCALCOSMOS_OPEN_SOURCE')

'''
    Home
'''
class AppsContextMixin:
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['apps'] = App.objects.all()
        return context


class ServerControlPanelHome(AppsContextMixin, TemplateView):
    template_name = 'server_control_panel/home.html'


class LCPrivateOnlyMixin:
    
    def dispatch(self, request, *args, **kwargs):
        if LOCALCOSMOS_OPEN_SOURCE == False:
            raise Http404('The resource you requested is only available on LC Private installations')
        return super().dispatch(request, *args, **kwargs)

'''
    Install App
    - only for LC Private installations
    - collect data and upload app .zip
'''
class InstallApp(LCPrivateOnlyMixin, FormView):
    template_name = 'server_control_panel/install_app.html'
    form_class = InstallAppForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localcosmos_apps_root'] = settings.LOCALCOSMOS_APPS_ROOT
        return context

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
                
        except:
            # could not import the zip
            # return an error
            error_message = _('Error importing the app. Please upload a valid app .zip file')
            errors.append(error_message)            

        if not errors:
            # create app object
            app_exists = App.objects.filter(uid=app_uid).exists()
            if app_exists:
                error_message = _('App already exists. You have to use the update feature.')
                errors.append(error_message)

            else:

                # the app uuid has to be the same as in app_settings, alongside other parameters
                app_folder = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, app_uid)
                app_path = os.path.join(app_folder, 'www')
                url = form.cleaned_data['url']
                cleaned_url = url.replace('https://', '').replace('http://', '')
                
                app = App(
                    uuid = app_uuid,
                    uid = app_uid,
                    name = app_name,
                    primary_language = primary_language,
                    published_version = app_version,
                    published_version_path = app_path,
                    url = cleaned_url
                )
                
                app.save()

                # create secondary languages
                for language in languages:
                    if language != primary_language:

                        secondary_language = SecondaryAppLanguages(
                            app=app,
                            language_code=language,
                        )

                        secondary_language.save()
                
                if os.path.isdir(app_folder):
                    shutil.rmtree(app_folder)

                # copy unzipped folder into app dir
                shutil.copytree(unzip_path, app_folder)

        # remove the temp folder
        shutil.rmtree(temp_folder)
            
        context['errors'] = errors
        
        return self.render_to_response(context)



'''
    AppMixin and App specific views
'''
class AppMixin(AppsContextMixin):
    
    def dispatch(self, request, *args, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        return super().dispatch(request, *args, **kwargs)


class CheckAppApiStatus(AppMixin, TemplateView):

    template_name = 'server_control_panel/app_api_status.html'

    def check_api_status(self):
        settings = self.app.get_settings(preview=False)

        result = {
            'success' : True,
            'error' : None,
        }
        
        api_url = api_url = settings['API_URL']

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
        

class AppDetail(AppMixin, TemplateView):

    template_name = 'server_control_panel/app_detail.html'
    
    

class UpdateApp(AppMixin, TemplateView):

    template_name = 'server_control_panel/update_app.html'
