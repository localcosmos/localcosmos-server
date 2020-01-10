from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.conf import settings
from django.urls import reverse
from django import forms
from django.utils.translation import gettext as _
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from localcosmos_server.generic_views import AjaxDeleteView

from .mixins import OnlineContentMixin

from .forms import (CreateTemplateContentForm, ManageTemplateContentForm, DeleteMicroContentForm, UploadFileForm,
                    UploadImageForm, UploadImageWithLicenceForm, TranslateTemplateContentForm)

from .models import (TemplateContent, LocalizedTemplateContent, TemplateContentFlags,
                     microcontent_category_model_map)

from .CMSObjects import CMSTag

import os


class ManageOnlineContent(OnlineContentMixin, TemplateView):

    template_name = 'online_content/online_content_base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        pages = TemplateContent.objects.filter(app=self.app, template_type='page')
        context['pages'] = pages

        features = TemplateContent.objects.filter(app=self.app, template_type='feature')
        context['features'] = features
        return context


'''
    Creating a template_content consists of
    - selecting a template
    - supplying a title
    - the title is always in the current language
'''
class CreateTemplateContent(OnlineContentMixin, FormView):

    template_name = 'online_content/create_template_content.html'
    form_class = CreateTemplateContentForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_type'] = self.kwargs['template_type']
        return context

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

        return redirect('manage_template_content', app_uid=self.app.uid, pk=template_content.pk)


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.app.primary_language
        return form_kwargs


    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.app, self.kwargs['template_type'], **self.get_form_kwargs())



'''
    Manage a Localized TemplateContent
    - The template is read and the content elements which the user has to fill are detected and presented in a form
'''

'''
    ManageMicroContents
    - Abstract View
    - Superclass for ManageTemplateContent and TranslateTemplateContent
    - self.language is not always the apps primary language, it can be the language of the translation
'''
class ManageMicroContents(OnlineContentMixin, FormView):

    template_name = 'online_content/manage_template_content.html'

    empty_text_microcontent_values = ['', '<p>&nbsp;</p>', None] # <p>&nbsp;</p> is an empty ckeditor field

    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(request, *args, **kwargs)
        self.set_language(request, *args, **kwargs)        
        return super().dispatch(request, *args, **kwargs)


    def set_template_content(self, request, *args, **kwargs):
        if not hasattr(self, 'template_content'):
            self.template_content = TemplateContent.objects.get(pk=kwargs['pk'])

    def set_language(self, request, *args, **kwargs):
        if not hasattr(self, 'language'):
            self.language = kwargs.get('language', self.template_content.app.primary_language)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['language'] = self.language
        context['template_content'] = self.template_content
        return context

    # this only saves in the draft models
    def _save_content(self, template_content, language, field, content, user):
        if hasattr(field, 'meta_instance') and field.meta_instance.pk:
            # translations always have the meta_instance, so no new meta_instance is created
            field.meta_instance.set_content(content, user, language)
        else:
            # the meta instance is created, which also triggers the creation of localized_instance
            # this should only be triggered when NOT translating
            meta_instance = field.cms_object.Model.objects.create(
                template_content,
                language,
                field.cms_object.microcontent_type,
                content,
                user,
            )

            # a multifield cant have ONE instance
            #if field.cms_object.multi == False:
            #    field.instance = instance

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.language
        return form_kwargs        
    
    def get_form(self):
        return self.form_class(self.template_content, **self.get_form_kwargs())

    # needed for reloading a clean form after POSTing
    def get_form_force_initial(self):
        form_kwargs = {
            'initial' : self.get_initial(),
            'language' : self.language,
        }
        return self.form_class(self.template_content, **form_kwargs)
        

    def save_localized_template_content(self, form):

        # translation_ready can only be set AFTER the microcontents have been saved
        # which is done after localized_template_content is saved
        
        self.localized_template_content.translation_ready = False
        self.localized_template_content.draft_title = form.cleaned_data['draft_title']
        self.localized_template_content.draft_navigation_link_name = form.cleaned_data['draft_navigation_link_name']
        self.localized_template_content.last_modified_by = self.request.user
        self.localized_template_content.save()

        secondary_languages = self.app.secondary_languages()

        if secondary_languages:
            # if the language is the primary language -> unready all other translations
            if self.localized_template_content.language == self.app.primary_language:

                for language in secondary_languages:
                    ltc = LocalizedTemplateContent.objects.filter(template_content=self.template_content,
                                                                  language=language).first()
                    if ltc:
                        ltc.translation_ready = False
                        ltc.save()

    # save the microcontent text fields
    def save_microcontent_fields(self, form, for_translation=False):

        language = form.cleaned_data['input_language']
        
        for field_ in form:

            field = field_.field
            if hasattr(field, 'cms_object'):

                data = form.cleaned_data[field_.name]
                
                if data and type(data) in [str, list] and len(data) > 0 and data not in self.empty_text_microcontent_values:

                    if type(data) == list:
                        for content in data:
                            self._save_content(self.template_content, language, field, content, self.request.user)
                    else:
                        self._save_content(self.template_content, language, field, data, self.request.user)
                
                else:
                    # do not delete image fields
                    if field.cms_object.microcontent_category not in ['image', 'images']:
                        # the user has submitted an empty field

                        # only delete the locale during translation
                        if for_translation == True:
                            if hasattr(field, 'localized_instance') and field.localized_instance.pk:
                                field.localized_instance.delete()
                        else:
                            # delete the field together with all translations
                            # if the user edits the primary language
                            if hasattr(field, 'meta_instance') and field.meta_instance.pk:
                                field.meta_instance.delete()
                

    def post(self, request, *args, **kwargs):
        context = {
            'saved_as_draft' : False,
        }

        form = self.get_form()

        if form.is_valid():

            # this saves localized_template_content
            # and then the microcontents
            # now, translatoin readyness can be checked
            self.form_valid(form)

            # optionally publish the template_content - if there are no secondary languages
            secondary_languages = self.app.secondary_languages()
            # if there are no secondary languages and translation-ready has been set, publish right away
            if 'translation-ready' in self.request.GET:

                if not secondary_languages:
                    # only one language exists -> try publication
                    publication_errors = self.localized_template_content.template_content.publish()
                    context['tried_publication'] = True
                    context['publication_errors'] = publication_errors

                else:
                    # more than one language present -> try to set translation_complete
                    translation_errors = self.localized_template_content.translation_complete()
                    context['tried_translation_ready'] = True
                    context['translation_errors'] = translation_errors

                    if not translation_errors:
                        self.localized_template_content.translation_ready = True
                        self.localized_template_content.save()

            else:
                context['saved_as_draft'] = True

            # necessary but not nice
            # using get_form_kwargs() will add 'data' and 'files' to the form
            # the form will then ignore the field.initial setting set by CMSObject
            form = self.get_form_force_initial()

        context.update(self.get_context_data(**kwargs))
        context['form'] = form
        return self.render_to_response(context)


'''
    fill a template content with microcontents in the main language
'''
class ManageTemplateContent(ManageMicroContents):

    form_class = ManageTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(request, *args, **kwargs)
        self.set_language(request, *args, **kwargs)

        self.localized_template_content = LocalizedTemplateContent.objects.filter(
            template_content=self.template_content, language=self.language).first()

        if not self.localized_template_content:
            # maybe the primary language has been changed
            # this requires the creation of a LocalizedTemplateContent in the primary language
            old_localized_template_content = LocalizedTemplateContent.objects.filter(
                template_content=self.template_content).first()
            ''' it is impossible that a localized_template_content does not exist for a template content
            if not temp_content:
                draft_title = _('Temporary Title')
                draft_navigation_link_name = _('Temporary Link name')
            else:
                draft_title = '[%s] %s' % (_('needs translation'), temp_content)
            '''
            draft_title = '[%s] %s' % (_('needs translation'), old_localized_template_content)
            draft_navigation_link_name = old_localized_template_content.draft_navigation_link_name
            self.localized_template_content = LocalizedTemplateContent.objects.create(request.user,
                                    self.template_content, self.language, draft_title, draft_navigation_link_name)

        # update preview_token if necessary
        token_is_valid = self.localized_template_content.validate_preview_token(
            self.localized_template_content.preview_token, 5) # 5 is maxminutes

        if token_is_valid == False:
            self.localized_template_content.update_preview_token()

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # make sure all data is up to date (!important)
        self.localized_template_content.refresh_from_db()
        context['localized_template_content'] = self.localized_template_content

        

        app_preview_url_suffix = '/online-content/%s/%s/' % (self.localized_template_content.slug,
                                                             self.localized_template_content.preview_token)

        # the relative preview url
        unschemed_preview_url = '{0}#{1}'.format(self.app.get_preview_url(), app_preview_url_suffix)

        # the host where the preview is served. on LCOS it is simply the website
        if unschemed_preview_url.startswith('http://') or unschemed_preview_url.startswith('https://'):
            preview_url = unschemed_preview_url
        else:
            preview_url = '{0}://{1}'.format(self.request.scheme, unschemed_preview_url)
        
        context['preview_url'] = preview_url
        context['preview'] = True
        
        return context


    def form_valid(self, form):
        # save the template_content, publication errors
        self.save_localized_template_content(form)

        flags = form.cleaned_data.get('page_flags', [])
        for page_flag in TemplateContentFlags.objects.filter(template_content=self.template_content):
            if page_flag.flag in flags:
                # remove from add_list
                flags.pop(flags.index(page_flag.flag))
            else:
                # delete db entry
                page_flag.delete()

        for f in flags:
            page_flag = TemplateContentFlags(
                template_content = self.template_content,
                flag = f,
            )
            page_flag.save()

        # save the microcontent
        self.save_microcontent_fields(form)
        

    def get_initial(self):
        
        initial = {
            'draft_title' : self.localized_template_content.draft_title,
            'draft_navigation_link_name' : self.localized_template_content.draft_navigation_link_name,
            'input_language' : self.localized_template_content.language,
            'page_flags' : self.localized_template_content.flags(),
        }
        return initial


'''
    above each field the source text/image needs to be shown
'''
class TranslateTemplateContent(ManageMicroContents):

    template_name = 'online_content/translate_template_content.html'
    form_class = TranslateTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        self.set_template_content(request, *args, **kwargs)

        # set_language reads the language from the kwargs first - in this case the target language
        self.set_language(request, *args, **kwargs)

        # fetch the new localized template_content if it already exists
        self.localized_template_content = LocalizedTemplateContent.objects.filter(
            template_content=self.template_content, language=self.language).first()

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['source_page'] = LocalizedTemplateContent.objects.get(
            language=self.app.primary_language, template_content=self.template_content)

        context['localized_template_content'] = self.localized_template_content

        # always show the draft content for translations
        context['preview'] = True
        return context

    def form_valid(self, form):

        # self.language is the target language

        # fetch or create the content
        self.localized_template_content = LocalizedTemplateContent.objects.filter(
            template_content=self.template_content, language=self.language).first()

        if not self.localized_template_content:
            self.localized_template_content = LocalizedTemplateContent.objects.create(
                self.request.user, self.template_content, self.language, form.cleaned_data['draft_title'],
                form.cleaned_data['draft_navigation_link_name'])
    
        # save the template_content
        self.save_localized_template_content(form)

        self.save_microcontent_fields(form, for_translation=True)

    # initial has to be overridden - localized_template_content mighjt not exist
    # initial['input_language'] is set by the LocalizeableForm and get_form_kwargs which
    # sets form_kwargs['language'] = self.language
    def get_initial(self):
        initial = {}

        if self.localized_template_content:
            initial['draft_title'] = self.localized_template_content.draft_title
            initial['draft_navigation_link_name'] = self.localized_template_content.draft_navigation_link_name
        
        return initial

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['for_translation'] = True
        return form_kwargs


    # needed for reloading a clean form after POSTing
    # override to inlude for_translation
    def get_form_force_initial(self):
        form_kwargs = {
            'initial' : self.get_initial(),
            'language' : self.language,
            'for_translation' : True,
        }
        return self.form_class(self.template_content, **form_kwargs)
        

'''
    publish all languages at once, or one language
'''
class PublishTemplateContent(OnlineContentMixin, TemplateView):

    template_name = 'online_content/template_content_list_entry.html'

    def dispatch(self, request, *args, **kwargs):

        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.language = kwargs.get('language', 'all')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['template_content'] = self.template_content
        context['publication'] = True
        context['publication_errors'] = self.template_content.publish(language=self.language)    

        return self.render_to_response(context)


class DeleteTemplateContent(AjaxDeleteView):
    model = TemplateContent


class UnpublishTemplateContent(OnlineContentMixin, TemplateView):

    template_name = 'online_content/ajax/unpublish_template_content.html'

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
        
    
"""
    this deletes draft_content of Textarea or TextInput fields, including CKEditor
    ajax is not used
    The content is not deleted - its draft_content is nullified. Otherwise, published content would vanish
"""
class DeleteMicroContent(OnlineContentMixin, TemplateView):

    template_name = 'online_content/delete_microcontent.html'
    form_class = DeleteMicroContentForm

    def dispatch(self, request, *args, **kwargs):
        self.kwargs = kwargs
        self.request = request
        
        self.language = kwargs['language']
        
        template_content_id = kwargs.get('template_content_id', None)
        self.template_content = None
        if template_content_id is not None:
            self.template_content = TemplateContent.objects.get(pk=template_content_id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_content'] = self.template_content
        context['language'] = self.language
        context['view_name'] = self.__class__.__name__
        return context


    def delete_microcontent(self, microcontent, language):
        # decide if only a translation is deleted - or if the content is deleted
        # if the language == primary_language we are not in the translation process, but
        # the main editor is editing the page -> delete microcontent and not localized_microcontent
        primary_language = microcontent.template_content.app.primary_language

        if language == primary_language:
            microcontent.delete()
        else:
            localized_microcontent = microcontent.get_localized(language)
            localized_microcontent.delete()
            
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        form = self.form_class(request.POST)

        success = False

        if form.is_valid():

            # published content has no delete button, it can only be unpublished
            Model = microcontent_category_model_map[form.cleaned_data['microcontent_category']]['draft']
            microcontent = Model.objects.filter(pk=form.cleaned_data['meta_pk']).first()

            if microcontent:
                localized_template_content = microcontent.template_content.get_localized(self.language)
                
                self.delete_microcontent(microcontent, self.language)

                # unready the translation
                localized_template_content.translation_ready = False
                localized_template_content.save()

            success = True

            context['success'] = success
            self.on_success(context, form)

        context['form'] = form
        context['success'] = success
        
        return self.render_to_response(context)


    def on_success(self, context, form):
        pass

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        initial = {
            'meta_pk' : request.GET['meta_pk'],
            'localized_pk' : request.GET['localized_pk'],
            'microcontent_category' : request.GET['microcontentcategory'],
            'microcontent_type' : request.GET.get('microcontenttype', None),
        }

        form = self.form_class(initial=initial)

        context.update({
            'form' : form,
        })
        
        return self.render_to_response(context)


# files are handled via ajax
class DeleteFileContent(DeleteMicroContent):


    def on_success(self, context, form):
        
        microcontent_category = form.cleaned_data['microcontent_category']
        microcontent_type = form.cleaned_data['microcontent_type']

        context['microcontent_category'] = microcontent_category
        context['microcontent_type'] = microcontent_type
        
        return self.render_to_response(context)


"""
    ajax upload file
    - in the future, language specific files should be possible
    - the form contains [pk],[template_content_id], language, file
    - the url kwargs contain microcontent_type, microcontent_category, language
"""
class UploadFile(OnlineContentMixin, TemplateView):

    template_name = 'online_content/filecontent_field_form.html'

    form_class = UploadFileForm

    def post(self, request, *args, **kwargs):

        microcontent_type = kwargs['microcontent_type'] # the microcontent_type as defined in the template
        microcontent_category = kwargs['microcontent_category']

        # if the form is invalid, language cannot be read from the form
        language = kwargs['language']
        
        cms_tag = CMSTag(microcontent_category, microcontent_type)

        widget_attrs = cms_tag._get_widget_attrs()

        form = self.form_class(request.POST, request.FILES)

        # this is not nice - it should be kwargs
        template_content_id = request.POST.get('template_content_id', None)
        template_content = None
        
        if template_content_id is not None:
            template_content = TemplateContent.objects.get(pk=template_content_id)

        if form.is_valid():
            pk = form.cleaned_data.get('pk', None)
            file = form.cleaned_data['file']
            
            language = form.cleaned_data['language']

            # Model is the Meta model: DraftImageMicroContent
            Model = microcontent_category_model_map[microcontent_category]['draft']

            if pk is not None:
                meta_instance = Model.objects.get(pk=form.cleaned_data['pk'])
                meta_instance.set_content(file, request.user, language)

            else:
                meta_instance = Model.objects.create(template_content, language, microcontent_type, file,
                                                     request.user)

            localized_instance = meta_instance.get_localized(language)

            field = cms_tag._create_field(language, meta_instance, localized_instance, widget_attrs=widget_attrs)

            # unready the localized translation/start a new version if published
            if template_content:
                localized_template_content = template_content.get_localized(language)
                localized_template_content.save()

        else:
            field = form.fields['file']

        fieldform = forms.Form()
        fieldform.fields[field['name']] = field['field']

        # fields do not render outside forms, we have to pass a form to the template

        context = {
            'fieldform' : fieldform,
            'form' : form,
            'template_content' : template_content,
            'language' : language,
        }
        
        return self.render_to_response(context)


class UploadImage(UploadFile):
    form_class = UploadImageForm


'''
    ManageFileUpload
    - a two-step process: opens a modal with image+licence input
    - requires the input of licences
'''
from content_licencing.view_mixins import LicencingFormViewMixin
class ManageImageUpload(LicencingFormViewMixin, OnlineContentMixin, FormView):

    template_name = 'online_content/ajax/image_microcontent_form.html'
    form_class = UploadImageWithLicenceForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.microcontent_category = kwargs['microcontent_category']
        
        self.MetaModel = microcontent_category_model_map[self.microcontent_category]['draft']
        self.LocaleModel = self.MetaModel.get_locale_model()

        self.template_content = None
        self.localized_instance = None
        self.meta_instance = None
        self.language = kwargs['language']
        
        if 'microcontent_id' in kwargs:
            self.meta_instance = self.MetaModel.objects.filter(pk=kwargs['microcontent_id']).first()
            self.localized_instance = self.meta_instance.get_localized(self.language)
            self.template_content = self.meta_instance.template_content
            self.microcontent_type = self.meta_instance.microcontent_type
        else:
            self.microcontent_type = kwargs['microcontent_type']
            self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])

        self.set_licence_registry_entry(self.localized_instance, 'content')
        return super().dispatch(request, *args, **kwargs)
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_content'] = self.template_content
        context['microcontent_category'] = self.microcontent_category
        context['microcontent_type'] = self.microcontent_type
        context['meta_instance'] = self.meta_instance
        context['localized_instance'] = self.localized_instance
        context['language'] = self.language
        return context


    def get_initial(self):
        initial = super().get_initial()

        if self.localized_instance:
            initial['source_image'] = self.localized_instance.content
            licencing_initial = self.get_licencing_initial()
            initial.update(licencing_initial)

        return initial
            

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.localized_instance:
            form_kwargs['current_image'] = self.localized_instance.content
        return form_kwargs
    

    def form_valid(self, form):

        image_file = form.cleaned_data['source_image']

        if not self.meta_instance:
            # this creates the localized_instance
            self.meta_instance = self.MetaModel.objects.create(self.template_content, self.language,
                                    self.microcontent_type, image_file, self.request.user)

        else:
            if not self.localized_instance or self.localized_instance.content != image_file:
                self.meta_instance.set_content(image_file, self.request.user, self.language)
        
        self.localized_instance = self.meta_instance.get_localized(self.language)
        # register content_licence
        self.register_content_licence(form, self.localized_instance, 'content')

        # render a response with refreshed data
        self.localized_instance.refresh_from_db()
        self.meta_instance.refresh_from_db()
        context = self.get_context_data(**self.kwargs)
        context['form'] = form

        return self.render_to_response(context)


'''
    get all fields for a microcontent_type
    ajax only
    for successful image deletions and uploads
    reloads all fields if field is multi
'''
from .CMSObjects import CMSTag
class GetFormField(OnlineContentMixin, FormView):

    template_name = 'online_content/ajax/reloaded_file_fields.html'
    form_class = forms.Form

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.template_content = TemplateContent.objects.get(pk=kwargs['template_content_id'])
        self.microcontent_category = kwargs['microcontent_category']
        self.microcontent_type = kwargs['microcontent_type']
        self.language = kwargs['language']
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['language'] = self.language
        context['template_content'] = self.template_content
        return context

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = forms.Form

        cms_tag = CMSTag(self.microcontent_category, self.microcontent_type)

        form = form_class(**self.get_form_kwargs())

        for field in cms_tag.form_fields(self.language, self.template_content):
            form.fields[field['name']] = field['field']
            form.fields[field['name']].language = self.language

        return form
