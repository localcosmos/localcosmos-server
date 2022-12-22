from django.shortcuts import redirect
from django.views.generic import TemplateView, FormView
from django import forms

from localcosmos_server.models import App
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.views import ManageServerContentImage, DeleteServerContentImage
from localcosmos_server.view_mixins import AppMixin

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from .models import TemplateContent, LocalizedTemplateContent
from .forms import CreateTemplateContentForm, ManageLocalizedTemplateContentForm, TranslateTemplateContentForm

from urllib.parse import urljoin


class TemplateContentList(AppMixin, TemplateView):

    template_name = 'template_content/template_content_base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        localized_template_contents = LocalizedTemplateContent.objects.filter(template_content__app=self.app,
            template_content__template_type='page', language=self.app.primary_language).order_by('pk')
        context['localized_template_contents'] = localized_template_contents

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
            form.cleaned_data['draft_navigation_link_name'],
            form.cleaned_data['template_name'],
            self.kwargs['template_type'],
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
        slug = ltc.slug

        template = self.template_content.draft_template

        template_url = template.definition['templateUrl'].replace('{slug}', slug)

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
                'draft_navigation_link_name' : self.localized_template_content.draft_navigation_link_name,
                'input_language' : self.localized_template_content.language,
            }

            if self.localized_template_content.draft_contents:
                for content_key, data in self.localized_template_content.draft_contents.items():
                    initial[content_key] = data
        
        return initial

    
    def save_localized_template_content(self, form):
        self.localized_template_content.draft_title = form.cleaned_data['draft_title']
        self.localized_template_content.draft_navigation_link_name = form.cleaned_data['draft_navigation_link_name']

        if not self.localized_template_content.draft_contents:
            self.localized_template_content.draft_contents = {}

        
        # existing keys in JSON - content that already has been saved
        old_keys = list(self.localized_template_content.draft_contents.keys())

        template_definition = self.localized_template_content.template_content.draft_template.definition

        for content_key, content_definition in template_definition['contents'].items():

            content = form.cleaned_data.get(content_key, None)

            if content and type(content) in [str, list] and len(content) > 0 and content not in self.empty_values:
                self.localized_template_content.draft_contents[content_key] = content

                if content_key in old_keys:
                    old_keys.remove(content_key)

                self.localized_template_content.draft_contents[content_key] = content

        # remove keys/data that do not occur anymore in the template
        for old_key in old_keys:
            del self.localized_template_content.draft_contents[old_key]

        self.localized_template_content.save()


class ManageLocalizedTemplateContent(ManageTemplateContentCommon, AppMixin, FormView):
    
    template_name = 'template_content/manage_localized_template_content.html'
    form_class = ManageLocalizedTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        self.localized_template_content = LocalizedTemplateContent.objects.get(pk=kwargs['localized_template_content_id'])
        self.template_content = self.localized_template_content.template_content
        self.language = self.localized_template_content.language
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        
        self.save_localized_template_content(form)

        context = self.get_context_data(**self.kwargs)
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
                self.language, form.cleaned_data['draft_title'], form.cleaned_data['draft_navigation_link_name'])

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
class GetTemplateContentFormFileFields(FormView):

    template_name = 'template_content/ajax/reloaded_file_fields.html'
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

        instances = self.localized_template_content.images(image_type=self.content_key).order_by('pk')
        field_manager = TemplateContentFormFieldManager(self.app, self.template_content, self.localized_template_content)
        form_fields = field_manager.get_form_fields(self.content_key, content_definition, instances)

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
    
