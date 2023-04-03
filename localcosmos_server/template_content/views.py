from django.shortcuts import redirect
from django.conf import settings
from django.views.generic import TemplateView, FormView
from django import forms

from localcosmos_server.models import App
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.views import ManageServerContentImage, DeleteServerContentImage
from localcosmos_server.view_mixins import AppMixin, FormLanguageMixin

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from .models import TemplateContent, LocalizedTemplateContent, Navigation, NavigationEntry, LocalizedNavigationEntry
from .forms import (CreateTemplateContentForm, ManageLocalizedTemplateContentForm, TranslateTemplateContentForm,
                    ManageNavigationForm, ManageNavigationEntryForm, ManageComponentForm)

from .utils import get_frontend_specific_url

from urllib.parse import urljoin

import uuid


class TemplateContentList(AppMixin, TemplateView):

    template_name = 'template_content/template_content_base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        localized_template_contents = LocalizedTemplateContent.objects.filter(template_content__app=self.app,
            template_content__template_type='page', language=self.app.primary_language, template_content__assignment=None).order_by('pk')
        context['localized_template_contents'] = localized_template_contents

        navigations = Navigation.objects.filter(app=self.app)
        context['navigations'] = navigations

        required_offline_contents = []
        if settings.LOCALCOSMOS_PRIVATE == False:
            app_settings = self.app.get_settings()

            pages = app_settings['templateContent'].get('requiredOfflineContents', {})
            for assignment, definition in pages.items():

                template_type = definition['templateType']

                template_content = TemplateContent.objects.filter(app=self.app, template_type=template_type,
                    assignment=assignment).first()

                content = {
                    'assignment': assignment,
                    'template_content': template_content,
                    'template_type': template_type,
                }

                required_offline_contents.append(content)

        context['required_offline_contents'] = required_offline_contents

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
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.app, self.kwargs['template_type'], **self.get_form_kwargs())


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
        
        if self.save_localized_template_content:
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

            if content_definition['type'] in ['image', 'component']:
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


    def get_initial(self):
        initial = super().get_initial()
        if self.component:
            initial['uuid'] = self.component['uuid']
        else:
            initial['uuid'] = uuid.uuid4()

        return initial


    def set_component(self, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        self.component_uuid = kwargs.pop('component_uuid', None)
        self.content_key = kwargs['content_key']
        
        # load the component template
        self.component = {}

        if self.component_uuid:
            self.component = self.localized_template_content.get_component(self.content_key, self.component_uuid)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_key'] = self.content_key
        context['component'] = self.component
        return context


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(self.app, self.template_content, self.localized_template_content, self.content_key, self.component, **self.get_form_kwargs())


    def form_valid(self, form):
        
        if not self.localized_template_content.draft_contents:
            self.localized_template_content.draft_contents = {}

        template = self.template_content.get_component_template(self.content_key)

        updated_component = self.get_updated_content_dict(template.definition, self.component, form)
        if not form.cleaned_data['uuid']:
            raise ValueError('uuid is missing')
        updated_component['uuid'] = str(form.cleaned_data['uuid'])

        self.localized_template_content.add_or_update_component(self.content_key, updated_component)

        self.localized_template_content.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


class DeleteComponent(TemplateView):

    template_name = 'template_content/ajax/delete_component.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_component(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_component(self, **kwargs):
        self.app = App.objects.get(uid=kwargs['app_uid'])
        self.localized_template_content = LocalizedTemplateContent.objects.get(pk=kwargs['localized_template_content_id'])
        
        self.content_key = kwargs['content_key']
        self.component_uuid = kwargs['component_uuid']
        
        self.component_template = self.localized_template_content.template_content.get_component_template(
            self.content_key)
        self.component_template_name = self.component_template.definition['templateName']
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app'] = self.app
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


'''
    use the same form / template as for the primary language
    but display the primary language abov ethe input fields
    display images, bu do not offer translations for images
'''
class TranslateTemplateContent(ManageTemplateContentCommon, AppMixin, FormView):
    
    template_name = 'template_content/translate_localized_template_content.html'
    form_class = TranslateTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.language = kwargs['language']
        self.localized_template_content = self.template_content.get_locale(self.language)
        return super().dispatch(request, *args, **kwargs)

    
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
from .forms import TemplateContentFormFieldManager
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



class ManageTemplateContentImage(ManageServerContentImage):

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
        context['content_key'] = self.content_key
        context['component_key'] = self.component_key
        context['component_uuid'] = self.component_uuid
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
            self.content_instance.add_or_update_component(self.component_key, new_component)
        super().save_image(form)


class DeleteComponentImage(ContextFromComponentIdentifier, DeleteTemplateContentImage):
    template_name = 'template_content/ajax/delete_component_image.html'

    def get_image_type(self):
        return self.object.image_type


'''
    publish all languages at once, or one language
'''
class PublishTemplateContent(AppMixin, TemplateView):

    template_name = 'template_content/template_content_list_entry.html'

    def dispatch(self, request, *args, **kwargs):

        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.localized_template_content = self.template_content.get_locale(
            self.template_content.app.primary_language)
        self.language = kwargs.get('language', 'all')

        return super().dispatch(request, *args, **kwargs)

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


class DeleteTemplateContent(AjaxDeleteView):
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


class DeleteNavigation(AjaxDeleteView):
    model = Navigation


class NavigationEntriesMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        navigation = Navigation.objects.get(pk=self.kwargs['pk'])
        context['navigation'] = navigation

        toplevel_entries = NavigationEntry.objects.filter(navigation=navigation, parent=None)
        context['navigation_entries'] = toplevel_entries
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


class DeleteNavigationEntry(AjaxDeleteView):
    model = NavigationEntry