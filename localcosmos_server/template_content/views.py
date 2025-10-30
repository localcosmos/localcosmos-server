from django.shortcuts import redirect
from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.http import JsonResponse
from django import forms

from localcosmos_server.models import App
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.views import ManageServerContentImageWithText, DeleteServerContentImage
from localcosmos_server.view_mixins import AppMixin, FormLanguageMixin

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from .models import (TemplateContent, LocalizedTemplateContent, Navigation, LocalizedNavigation,
                     NavigationEntry, LocalizedNavigationEntry)
from .forms import (CreateTemplateContentForm, ManageLocalizedTemplateContentForm, TranslateTemplateContentForm,
                    ManageNavigationForm, ManageNavigationEntryForm, ManageComponentForm, TranslateNavigationForm,
                    TemplateContentFormFieldManager)

from .utils import get_frontend_specific_url

from .Templates import Template

from urllib.parse import urljoin

import uuid, json


class TemplateContentList(AppMixin, TemplateView):

    template_name = 'template_content/template_content_base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # check if the frontend supports navigations
        frontend_settings = self.app.get_settings()
        supports_navigations = False

        if 'templateContent' in frontend_settings and 'navigations' in frontend_settings['templateContent']:
            supports_navigations = True

        context['supports_navigations'] = supports_navigations
        
        localized_template_contents = LocalizedTemplateContent.objects.filter(template_content__app=self.app,
            template_content__template_type='page', language=self.app.primary_language, template_content__assignment=None).order_by('pk')
        
        found_template_content_ids = list(localized_template_contents.values_list('template_content__pk', flat=True))
        
        context['localized_template_contents'] = localized_template_contents

        navigations = Navigation.objects.filter(app=self.app)
        context['navigations'] = navigations

        required_offline_contents = []
        
        # offline contents are always manged within the app kit
        if settings.LOCALCOSMOS_PRIVATE == False:
                        
            app_settings = self.app.get_settings()
            
            if 'templateContent' in app_settings:

                required_contents = app_settings['templateContent'].get('requiredOfflineContents', {})
                for assignment, definition in required_contents.items():

                    template_type = definition['templateType']

                    template_content = TemplateContent.objects.filter(app=self.app, template_type=template_type,
                        assignment=assignment).first()
                    
                    if template_content:
                        found_template_content_ids.append(template_content.pk)

                    content = {
                        'assignment': assignment,
                        'template_content': template_content,
                        'template_type': template_type,
                    }

                    required_offline_contents.append(content)
            
        
        context['required_offline_contents'] = required_offline_contents

        # unsupported template contents
        unsupported_contents = LocalizedTemplateContent.objects.filter(template_content__app=self.app, template_content__template_type='page',
            language=self.app.primary_language).exclude(template_content__pk__in=found_template_content_ids).order_by('pk')
            
        context['unsupported_contents'] = unsupported_contents

        return context


'''
    Creating a template_content consists of
    - selecting a template
    - supplying a title
    - the title is always in the current language
'''
class CreateTemplateContent(AppMixin, FormView):

    template_name = 'template_content/create_template_content.html'
    form_class = CreateTemplateContentForm


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_type'] = self.kwargs['template_type']
        context['assignment'] = self.kwargs.get('assignment', None)
        return context


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.app.primary_language
        return form_kwargs


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.app, **self.get_form_kwargs())


    def form_valid(self, form):
        # create a new template_content for this online content (which is app specific)

        template_content = TemplateContent.objects.create(
            self.request.user,
            self.app,
            self.app.primary_language,
            form.cleaned_data['draft_title'],
            form.cleaned_data['template_name'],
            self.kwargs['template_type'],
            self.kwargs.get('assignment', None),
        )

        template_content.save()

        localized_template_content = template_content.get_locale(self.app.primary_language)

        return redirect('manage_localized_template_content', app_uid=self.app.uid,
            localized_template_content_id=localized_template_content.pk)


class ManageTemplateContentCommon:

    empty_values = ['', '<p>&nbsp;</p>', None]

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.app, self.template_content, self.localized_template_content, **self.get_form_kwargs())

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.language
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_template_content'] = self.localized_template_content
        context['template_content'] = self.template_content
        context['preview_url'] = self.get_preview_url()
        context['language'] = self.language
        return context

    def get_preview_url(self):

        #if self.localized_template_content:
        #    slug = self.localized_template_content.slug
        #else:
        ltc = self.template_content.get_locale(self.app.primary_language)

        app_settings = self.app.get_settings()
        template_url = get_frontend_specific_url(app_settings, ltc)

        # the relative preview url
        app_preview_url = self.app.get_preview_url()

        unschemed_preview_url = urljoin(app_preview_url, template_url.lstrip('/'))

        # the host where the preview is served. on LCOS it is simply the website
        if unschemed_preview_url.startswith('http://') or unschemed_preview_url.startswith('https://'):
            preview_url = unschemed_preview_url
        else:
            preview_url = '{0}://{1}'.format(self.request.scheme, unschemed_preview_url)
        
        return preview_url


    def get_initial(self):

        initial = {}
        
        if self.localized_template_content:
            initial = {
                'draft_title' : self.localized_template_content.draft_title,
                'input_language' : self.localized_template_content.language,
            }

            if self.localized_template_content.draft_contents:
                for content_key, data in self.localized_template_content.draft_contents.items():
                    initial[content_key] = data
        
        return initial


    def get_updated_content_dict(self, template_definition, existing_dict, form):

        app_settings = self.app.get_settings()

        # existing keys in JSON - content that already has been saved
        old_keys = list(existing_dict.keys())

        for content_key, content_definition in template_definition['contents'].items():

            if content_definition['type'] in ['image', 'component', 'stream']:
                if content_key in old_keys:
                    old_keys.remove(content_key)

            content = form.cleaned_data.get(content_key, None)

            if content:

                if content_definition['type'] in ['text']:
                
                    if type(content) in [str, list] and len(content) > 0 and content not in self.empty_values:
                        existing_dict[content_key] = content

                elif content_definition['type'] in ['templateContentLink']:

                    ltc = content

                    template_name = ltc.template_content.draft_template_name

                    url = app_settings['templateContent']['urlPattern'].replace('{slug}', content.slug).replace('{templateName}', template_name)

                    existing_dict[content_key] = {
                        'pk': str(ltc.pk),
                        'slug': ltc.slug,
                        'templateName': template_name,
                        'title': ltc.published_title,
                        'url': url,
                    }

                if content_key in old_keys:
                    old_keys.remove(content_key)

        # remove keys/data that do not occur anymore in the template
        for old_key in old_keys:
            del existing_dict[old_key]
        
        return existing_dict
    
    def save_localized_template_content(self, form):
        self.localized_template_content.draft_title = form.cleaned_data['draft_title']

        if not self.localized_template_content.draft_contents:
            self.localized_template_content.draft_contents = {}

        template_definition = self.localized_template_content.template_content.draft_template.definition
        existing_dict = self.localized_template_content.draft_contents
        
        updated_dict = self.get_updated_content_dict(template_definition, existing_dict, form)

        self.localized_template_content.draft_contents = updated_dict

        self.localized_template_content.save()



class WithLocalizedTemplateContent:

    def set_template_content(self, **kwargs):
        self.localized_template_content = LocalizedTemplateContent.objects.get(pk=kwargs['localized_template_content_id'])
        self.template_content = self.localized_template_content.template_content
        self.language = self.localized_template_content.language


class ManageLocalizedTemplateContent(ManageTemplateContentCommon, AppMixin, WithLocalizedTemplateContent, FormView):
    
    template_name = 'template_content/manage_localized_template_content.html'
    form_class = ManageLocalizedTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(**kwargs)    
        return super().dispatch(request, *args, **kwargs)
    
    def get_in_app_url(self):
        app_settings = self.app.get_settings()
        url_pattern = app_settings['templateContent']['urlPattern']
        url = url_pattern.replace('{slug}', self.localized_template_content.slug).replace('{templateName}', self.template_content.draft_template_name)
        return url
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_in_app'] = self.get_in_app_url()
        return context

    def form_valid(self, form):
        
        self.save_localized_template_content(form)

        context = self.get_context_data(**self.kwargs)
        return self.render_to_response(context)

        

class ManageComponent(ManageTemplateContentCommon, AppMixin, WithLocalizedTemplateContent, FormView):

    template_name = 'template_content/ajax/manage_component.html'
    form_class = ManageComponentForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(**kwargs)
        self.set_component(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    
    def set_component(self, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        self.component_uuid = kwargs.pop('component_uuid', None)
        self.content_key = kwargs['content_key']
        
        # load the component template
        self.component = {}
        self.component_template_name = None

        if self.component_uuid:
            self.component = self.localized_template_content.get_component(self.content_key, self.component_uuid)
            self.component_template_name = self.component.get('templateName', None)
        
        
        if not self.component_template_name:
            if 'component_template_name' in kwargs:
                self.component_template_name = kwargs['component_template_name']
            else:
                page_template_definition = self.template_content.draft_template.definition
                self.component_template_name = page_template_definition['contents'][self.content_key]['templateName']
                
        if not self.component_template_name:
            raise ValueError('component_template_name is missing')


    def get_initial(self):
        # do not use super() because it would add contents of localized_template_content to initial
        initial = {
            'input_language': self.localized_template_content.language,
        }
        if self.component:
            initial['uuid'] = self.component['uuid']
        else:
            initial['uuid'] = uuid.uuid4()
        return initial


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_key'] = self.content_key
        context['component'] = self.component
        context['component_template_name'] = self.component_template_name
        return context


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(self.app, self.template_content, self.localized_template_content, self.content_key, self.component_template_name,
                          self.component, **self.get_form_kwargs())


    def form_valid(self, form):
        
        if not self.localized_template_content.draft_contents:
            self.localized_template_content.draft_contents = {}

        component_template = Template(self.app, self.component_template_name, 'component')

        updated_component = self.get_updated_content_dict(component_template.definition, self.component, form)
        if not form.cleaned_data['uuid']:
            raise ValueError('uuid is missing')
        updated_component['uuid'] = str(form.cleaned_data['uuid'])
        updated_component['templateName'] = self.component_template_name

        self.localized_template_content.add_or_update_component(self.content_key, updated_component)

        self.localized_template_content.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)
        

class DeleteComponent(AppMixin, TemplateView):

    template_name = 'template_content/ajax/delete_component.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_component(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_component(self, **kwargs):
        self.localized_template_content = LocalizedTemplateContent.objects.get(pk=kwargs['localized_template_content_id'])
        
        self.content_key = kwargs['content_key']
        self.component_uuid = kwargs['component_uuid']
        
        self.component = self.localized_template_content.get_component(self.content_key, self.component_uuid)
        
        if not self.component:
            raise ValueError(f'Component {self.component_uuid} not found')
        
        self.component_template_name = self.component.get('templateName', None)
        
        if not self.component_template_name:
        
            component_template = self.localized_template_content.template_content.get_component_template(
                self.content_key)
            
            if component_template.definition['type'] == 'stream':
                raise ValueError('Failed to get component_template_name.')
            else:
                self.component_template_name = component_template.definition['templateName']
                

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_template_content'] = self.localized_template_content
        context['content_key'] = self.content_key
        context['component_uuid'] = self.component_uuid
        context['component_template_name'] = self.component_template_name
        context['deleted'] = False
        return context

    def post(self, request, *args, **kwargs):
        
        self.localized_template_content.remove_component(self.content_key, self.component_uuid)

        context = self.get_context_data(**kwargs)
        context['deleted'] = True
        return self.render_to_response(context)



class StoreComponentOrder(AppMixin, TemplateView):
    
    @method_decorator(ajax_required)
    def post(self, request, *args, **kwargs):

        success = False

        order = request.POST.get('order', None)

        if order:
            
            order = json.loads(order)
            
            localized_template_content = LocalizedTemplateContent.objects.get(pk=kwargs['localized_template_content_id'])
            content_key = kwargs['content_key']
            
            content_definition = localized_template_content.template_content.draft_template.definition['contents'][content_key]
            
            if not content_definition or content_definition['type'] != 'stream':
                return JsonResponse({'success':False, 'error':'Content is not a stream'})

            existing_components = localized_template_content.draft_contents.get(content_key, [])

            ordered_components = []
            for component_uuid in order:
                
                for component in existing_components:
                    if component['uuid'] == component_uuid:
                        ordered_components.append(component)
                        break
                    
            # make sure nothing gets lost
            if len(ordered_components) != len(existing_components):
                return JsonResponse({'success':False, 'error':'Components got lost.'})
            
            localized_template_content.draft_contents[content_key] = ordered_components
            localized_template_content.save()
            success = True
        
        return JsonResponse({'success':success})
'''
    use the same form / template as for the primary language
    but display the primary language above the input fields
'''
class TranslateTemplateContent(ManageTemplateContentCommon, AppMixin, FormView):
    
    template_name = 'template_content/translate_localized_template_content.html'
    form_class = TranslateTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_template_content(self, **kwargs):
        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.language = kwargs['language']
        self.localized_template_content = self.template_content.get_locale(self.language)
        
    
    def form_valid(self, form):

        self.localized_template_content = self.template_content.get_locale(self.language)

        if not self.localized_template_content:
            self.localized_template_content = LocalizedTemplateContent.objects.create(self.request.user, self.template_content,
                self.language, form.cleaned_data['draft_title'])

        self.save_localized_template_content(form)

        context = self.get_context_data(**self.kwargs)
        return self.render_to_response(context)
        

'''
    get all fields for a content_key
    ajax only
    for successful image deletions and uploads
    reloads all fields if field is multi
'''
class GetTemplateContentFormFields(FormView):

    template_name = 'template_content/ajax/reloaded_form_fields.html'
    form_class = forms.Form

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_content(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_content(self, **kwargs):
        self.localized_template_content = LocalizedTemplateContent.objects.get(pk=kwargs['localized_template_content_id'])
        self.template_content = self.localized_template_content.template_content
        self.app = self.template_content.app
        self.content_key = kwargs['content_key']
    

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = forms.Form

        form = form_class(**self.get_form_kwargs())

        template_definition = self.localized_template_content.template_content.draft_template.definition

        content_definition = template_definition['contents'][self.content_key]

        field_manager = TemplateContentFormFieldManager(self.app, self.template_content, self.localized_template_content)
        form_fields = field_manager.get_form_fields(self.content_key, content_definition)

        for field in form_fields:
            form.fields[field['name']] = field['field']

        return form



class ManageTemplateContentImage(AppMixin, ManageServerContentImageWithText):

    template_name = 'template_content/ajax/manage_template_content_image.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_template_content'] = self.content_instance
        context['content_key'] = self.image_type

        return context



class DeleteTemplateContentImage(DeleteServerContentImage):

    template_name = 'template_content/ajax/delete_template_content_image.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_template_content'] = self.object.content
        context['content_key'] = self.object.image_type
        return context


'''
    Create the component with its uuid
    Upload the image
    Go Back to the component Modal

    image identifiers for components:
    LocalizedTemplatecontent.image: component_key:component_uuid:content_key
'''
class ContextFromComponentIdentifier:

    def get_image_type(self):
        return self.image_type

    def set_component(self):
        image_type = self.get_image_type()
        content_identifiers = image_type.split(':')
        
        self.content_key = content_identifiers[-1]
        self.component_key = content_identifiers[0]
        self.component_uuid = content_identifiers[1]
            

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_component()
        context['content_key'] = self.content_key # the field in page.contents
        context['component_key'] = self.component_key # page.contents[content_key][component_key] - the key that holds the image
        context['component_uuid'] = self.component_uuid # the uuid of the component instance
        return context


class ManageComponentImage(ContextFromComponentIdentifier, ManageTemplateContentImage):
    template_name = 'template_content/ajax/manage_component_image.html'

    # if the user uploads an image before saving the component, save the component here
    def save_image(self, form):
        self.set_component()
        # check if component exits, and save if if not
        
        component = self.content_instance.get_component(self.component_key, self.component_uuid)

        if not component:
            new_component = {
                'uuid': self.component_uuid
            }

            # add component to page contents -> we need a component_uuid
            self.content_instance.add_or_update_component(self.component_key, new_component)
        super().save_image(form)


class DeleteComponentImage(AppMixin, ContextFromComponentIdentifier, DeleteTemplateContentImage):
    template_name = 'template_content/ajax/delete_component_image.html'

    def get_image_type(self):
        return self.object.image_type


'''
    publish all languages at once, or one language
'''
class PublishTemplateContent(AppMixin, TemplateView):

    template_name = 'template_content/template_content_list_entry.html'

    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_template_content(self, **kwargs):
        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.localized_template_content = self.template_content.get_locale(
            self.template_content.app.primary_language)
        self.language = kwargs.get('language', 'all')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_template_content'] = self.localized_template_content
        context['template_content'] = self.template_content
        context['publication'] = True
        context['publication_errors'] = self.template_content.publish(language=self.language)    

        return context


class UnpublishTemplateContent(AppMixin, TemplateView):

    template_name = 'template_content/ajax/unpublish_template_content.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_content'] = self.template_content
        context['success'] = False
        return context


    def post(self, request, *args, **kwargs):
        self.template_content.unpublish()
        context = self.get_context_data(**kwargs)
        context['success'] = True
        return self.render_to_response(context)


class DeleteTemplateContent(AppMixin, AjaxDeleteView):
    model = TemplateContent
    

class ManageNavigation(AppMixin, FormLanguageMixin, FormView):

    template_name = 'template_content/ajax/manage_navigation.html'
    form_class = ManageNavigationForm


    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_navigation(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_navigation(self, **kwargs):
        self.navigation = None
        if 'pk' in kwargs:
            self.navigation = Navigation.objects.get(pk=kwargs['pk'])


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navigation'] = self.navigation
        context['success'] = False
        return context


    def get_initial(self):
        initial = super().get_initial()
        if self.navigation:
            initial['name'] = str(self.navigation)
            initial['navigation_type'] = self.navigation.navigation_type
        return initial


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['navigation'] = self.navigation
        return form_kwargs


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.app, **self.get_form_kwargs())


    def form_valid(self, form):

        if not self.navigation:
            self.navigation = Navigation.objects.create(self.app, form.cleaned_data['navigation_type'],
                self.app.primary_language, form.cleaned_data['name'])

        self.navigation.navigation_type = form.cleaned_data['navigation_type']
        self.navigation.save()

        localized_navigation = self.navigation.get_locale(self.app.primary_language)
        localized_navigation.name = form.cleaned_data['name']
        localized_navigation.save()
        
        context = self.get_context_data(**self.kwargs)

        context['success'] = True
        return self.render_to_response(context)



class PublishNavigation(AppMixin, TemplateView):

    template_name = 'template_content/ajax/navigation_list_entry.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_navigation(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_navigation(self, **kwargs):
        self.navigation = Navigation.objects.get(pk=kwargs['navigation_id'])
        self.localized_navigation = self.navigation.get_locale(
            self.navigation.app.primary_language)
        self.language = kwargs.get('language', 'all')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_navigation'] = self.localized_navigation
        context['navigation'] = self.navigation
        context['publication'] = True
        context['publication_errors'] = self.navigation.publish(language=self.language)    

        return context


class DeleteNavigation(AppMixin, AjaxDeleteView):
    model = Navigation


class NavigationEntriesMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        navigation = Navigation.objects.get(pk=self.kwargs['pk'])
        context['navigation'] = navigation
        
        
        max_entries = navigation.settings.get('maxEntries', None)

        toplevel_entries = NavigationEntry.objects.filter(navigation=navigation, parent=None)
        if max_entries:
            toplevel_entries = toplevel_entries[:max_entries]
        context['navigation_entries'] = toplevel_entries
        context['max_entries'] = max_entries
        return context


class ManageNavigationEntries(NavigationEntriesMixin, AppMixin, TemplateView):
    
    template_name = 'template_content/manage_navigation_entries.html'


class GetNavigationEntriesTree(NavigationEntriesMixin, AppMixin, TemplateView):

    template_name = 'template_content/ajax/navigation_entries_tree.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class ManageNavigationEntry(AppMixin, FormLanguageMixin, FormView):
    
    template_name = 'template_content/ajax/manage_navigation_entry.html'
    form_class = ManageNavigationEntryForm

    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_navigation(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_navigation(self, **kwargs):
        self.navigation = Navigation.objects.get(pk=kwargs['navigation_id'])
        self.navigation_entry = None
        if 'pk' in kwargs:
            self.navigation_entry = NavigationEntry.objects.get(pk=kwargs['pk'])


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navigation'] = self.navigation
        context['navigation_entry'] = self.navigation_entry
        context['success'] = False
        return context


    def get_initial(self):
        initial = super().get_initial()
        if self.navigation_entry:
            primary_locale_navigation_entry = LocalizedNavigationEntry.objects.filter(
                navigation_entry=self.navigation_entry, language=self.app.primary_language
            ).first()
            if primary_locale_navigation_entry:
                initial['link_name'] = primary_locale_navigation_entry.link_name
            initial['template_content'] = self.navigation_entry.template_content
            initial['parent'] = self.navigation_entry.parent
        return initial



    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['navigation_entry'] = self.navigation_entry
        return form_kwargs


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.navigation, **self.get_form_kwargs())


    def form_valid(self, form):
        
        if not self.navigation_entry:
            self.navigation_entry = NavigationEntry(
                navigation=self.navigation,
            )

        self.navigation_entry.template_content = form.cleaned_data['template_content']
        self.navigation_entry.parent = form.cleaned_data.get('parent', None)

        # somehow set url

        self.navigation_entry.save()

        primary_locale_navigation_entry = self.navigation_entry.get_locale(self.app.primary_language)
        if not primary_locale_navigation_entry:
            primary_locale_navigation_entry = LocalizedNavigationEntry(
                navigation_entry=self.navigation_entry,
                language=self.app.primary_language,
            )
        
        primary_locale_navigation_entry.link_name = form.cleaned_data['link_name']
        primary_locale_navigation_entry.save()        

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        
        return self.render_to_response(context)


class DeleteNavigationEntry(AppMixin, AjaxDeleteView):
    model = NavigationEntry


class ComponentContentView(ManageComponent):

    template_name = 'template_content/ajax/component_content_view.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(**kwargs)
        self.set_component(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_template_content(self, **kwargs):
        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.app = self.template_content.app
        self.language = self.app.primary_language
        self.localized_template_content = self.template_content.get_locale(self.language)


class TranslateNavigation(AppMixin, FormView):
    
    template_name = 'template_content/translate_localized_navigation.html'
    form_class = TranslateNavigationForm

    def dispatch(self, request, *args, **kwargs):
        self.set_navigation(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_navigation(self, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        self.navigation = Navigation.objects.get(pk=kwargs['pk'])
        self.language = kwargs['language']
        self.localized_navigation = self.navigation.get_locale(self.language)
        self.primary_locale_navigation = self.navigation.get_locale(self.app.primary_language)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['localized_navigation'] = self.localized_navigation
        context['navigation'] = self.navigation
        context['primary_locale_navigation'] = self.primary_locale_navigation
        context['language'] = self.language
        context['saved'] = False
        return context
    

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.language
        return form_kwargs
    
    
    def get_initial(self):
        initial = super().get_initial()
        if self.localized_navigation:
            initial['name'] = self.localized_navigation.name
        return initial


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.app, self.navigation, **self.get_form_kwargs())
    

    def save_localized_navigation(self, form):
        
        for field in form:

            if hasattr(field.field, 'navigation_entry'):

                navigation_entry = field.field.navigation_entry
                localized_navigation_entry = navigation_entry.get_locale(self.language)

                link_name = form.cleaned_data.get(field.name, '')

                if not link_name or link_name == '':
                    if localized_navigation_entry:
                        localized_navigation_entry.delete()

                else:
                    if not localized_navigation_entry:
                        localized_navigation_entry = LocalizedNavigationEntry(
                            navigation_entry = navigation_entry,
                            language = self.language,
                        )
                        
                    localized_navigation_entry.link_name = link_name
                    localized_navigation_entry.save()

    def form_valid(self, form):

        if not self.localized_navigation:
            self.localized_navigation = LocalizedNavigation.objects.create(self.navigation, self.language,
                                                                           form.cleaned_data['name'])

        self.save_localized_navigation(form)

        context = self.get_context_data(**self.kwargs)
        context['saved'] = True
        return self.render_to_response(context)