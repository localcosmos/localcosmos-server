from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _

import os

from .parser import TemplateParser
from .models import NAVIGATION_LINK_NAME_MAX_LENGTH, TemplateContent

from django.template import loader

from django.contrib.auth import get_user_model

from localcosmos_server.forms import LocalizeableForm

User = get_user_model()


class TemplateContentFormCommon(LocalizeableForm):
    draft_title = forms.CharField(label=_('Title'))
    draft_navigation_link_name = forms.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH, label=_('Link name in navigations'),
            help_text=_('Max %(characters)s characters. If this content shows up in a navigation this name will be shown as the link.') % {'characters' : NAVIGATION_LINK_NAME_MAX_LENGTH})

    localizeable_fields = ['draft_title', 'draft_navigation_link_name']


class CreateTemplateContentForm(TemplateContentFormCommon):
    
    template_name = forms.ChoiceField(label =_('Template'))

    def __init__(self, app, template_type, *args, **kwargs):

        self.app = app
        self.template_type = template_type
        
        super().__init__(*args, **kwargs)

        # load the template_choices according to the cms
        choices = app.get_online_content_templates(template_type)
        self.fields['template_name'].choices = choices


'''
    there are global contents without page (eg on base.html)
    and contents bound to a page    
'''
class ManageMicroContentsForm(TemplateContentFormCommon):

    def _append_additional_fields(self):
        pass

    def _template(self):
        return self.template_content.get_template()

    def __init__(self, template_content, *args, **kwargs):

        self.template_content = template_content

        for_translation = kwargs.pop('for_translation', False)
        
        super().__init__(*args, **kwargs)

        self._append_additional_fields()

        self.layoutable_full_fields = set([])
        self.layoutable_simple_fields = set([])

        # read the template and find microcontent
        template = self._template()

        # find all cms template tags in source
        parser = TemplateParser(template_content.app, template_content, template)
        cms_tags = parser.parse()

        # the fields should be in self.fields        
        for tag in cms_tags:

            # get cms form fields for each tag
            for field in tag.form_fields(self.language, template_content, for_translation=for_translation):
                
                self.fields[field['name']] = field['field']

                self.fields[field['name']].language = self.language
                
                if 'layoutable-simple' in tag.args:
                    self.layoutable_simple_fields.add(field['name'])
                elif 'layoutable-full' in tag.args:
                    self.layoutable_full_fields.add(field['name'])


class ManageTemplateContentForm(ManageMicroContentsForm):
    
    #draft_title = forms.CharField(label=_('Title'))
    #draft_navigation_link_name = forms.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH, label=_('Link name in navigations'),
    #        help_text=_('Max %(characters)s characters. If this content shows up in a navigation this name will be shown as the link.') % {'characters' : NAVIGATION_LINK_NAME_MAX_LENGTH})
    page_flags = forms.MultipleChoiceField(label=_('Show link to this online content in'), required=False,
                    help_text=_('The title will be the name of the link in the navigations. Long titles will be cut off.'))


    def _append_additional_fields(self):
        # read the theme conf and add the page types defined there
        theme_settings = self.template_content.get_theme_settings()

        page_flag_choices = []
        
        for navigation_type, navigation in theme_settings['flags'].items():
            page_flag_choices.append(
                (navigation_type, _(navigation['name']))
            )

        for section, definition in theme_settings['sections'].items():
            page_flag_choices.append(
                (section, _(section))
            )

        if self.template_content.template_type == 'page':
            self.fields['page_flags'].choices = page_flag_choices
        else:
            self.fields.pop('page_flags')

        if not page_flag_choices and 'page_flags' in self.fields:
            self.fields.pop('page_flags')


'''
    Translate Template Content
    - do not include page_flags
'''
class TranslateTemplateContentForm(ManageMicroContentsForm):
    pass


class ManagePagebaseForm(ManageMicroContentsForm):

    def __init__(self, template, *args, **kwargs):
        self.template = template
        super().__init__(None, language, *args, **kwargs)

    def _template(self):
        return self.template
    

'''
    currently, this is only used in the primary language and deletes the meta_instance
    if the localized_instance should be deleted only (-> translations), a rewrite is needed
'''
class DeleteMicroContentForm(forms.Form):
    meta_pk = forms.IntegerField(widget=forms.HiddenInput)
    localized_pk = forms.IntegerField(widget=forms.HiddenInput)
    microcontent_category = forms.CharField(widget=forms.HiddenInput)
    microcontent_type = forms.CharField(widget=forms.HiddenInput, required=False)


class UploadFileForm(forms.Form):
    # used urlparam instead: if form is invalid render an empty input with error message
    # microcontent_category = forms.CharField()
    # microcontent_type = forms.CharField()
    pk = forms.IntegerField(widget=forms.HiddenInput, required=False)
    template_content_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    language = forms.ChoiceField(widget=forms.HiddenInput, choices=settings.LANGUAGES)
    file = forms.FileField()


class UploadImageForm(UploadFileForm):
    file = forms.ImageField()

from content_licencing.mixins import LicencingFormMixin
from collections import OrderedDict
from localcosmos_server.widgets import ImageInputWithPreview
from localcosmos_server.forms import ManageContentImageFormCommon
class UploadImageWithLicenceForm(ManageContentImageFormCommon, LicencingFormMixin, forms.Form):

    template_content_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def get_source_image_field(self):
        # unfortunately, a file field cannot be prepoluated due to html5 restrictions
        # therefore, source_image has to be optional. Otherwise, editing would be impossible
        # check if a new file is required in clean
        source_image_field = forms.ImageField(widget=ImageInputWithPreview, required=False)
        source_image_field.widget.current_image = self.current_image

        return source_image_field
