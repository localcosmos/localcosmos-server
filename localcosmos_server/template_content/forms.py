from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from .models import NAVIGATION_LINK_NAME_MAX_LENGTH

from .Templates import Template, Templates

from django.contrib.auth import get_user_model

from localcosmos_server.forms import LocalizeableForm

import re

User = get_user_model()


class TemplateContentFormCommon(LocalizeableForm):
    draft_title = forms.CharField(label=_('Title'))
    draft_navigation_link_name = forms.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH,
            label=_('Name for links in navigation menus'),
            help_text=_('Max %(characters)s characters. If this content shows up in a navigation menu, this name will be shown as the link.') % {'characters' : NAVIGATION_LINK_NAME_MAX_LENGTH})

    localizeable_fields = ['draft_title', 'draft_navigation_link_name']


class CreateTemplateContentForm(TemplateContentFormCommon):
    
    template_name = forms.ChoiceField(label =_('Template'))

    def __init__(self, app, template_type, *args, **kwargs):

        self.app = app
        self.template_type = template_type
        
        super().__init__(*args, **kwargs)

        # load the template_choices
        templates = Templates(self.app)
        available_templates = templates.get_all_templates()

        choices = []

        if available_templates:
            for template_name, template in available_templates.items():
                choice = (template_name, template.definition['templateName'])
                choices.append(choice)
        self.fields['template_name'].choices = choices


# translations initially do not supply a localized_template_content
class TemplateContentFormFieldManager:

    def __init__(self, app, template_content, localized_template_content=None):
        self.template_content = template_content
        self.localized_template_content = localized_template_content
        self.primary_locale_template_content = template_content.get_locale(app.primary_language)

    def get_form_fields(self, content_key, content_definition, instances):

        form_fields = []
        draft_contents = {}

        if self.localized_template_content and self.localized_template_content.draft_contents:
            draft_contents = self.localized_template_content.draft_contents

        if content_definition['type'] == 'multi-image':

            max_number = content_definition.get('max_number', None)

            is_first = True
            is_last = False
            field_count = 0

            for current_image in instances:

                field_count += 1

                form_field = self.get_image_form_field(content_key, content_definition, current_image)

                if field_count == max_number:
                    is_last = True

                form_field.is_first = is_first
                form_field.is_last = is_last
                
                field_name = '{0}-{1}'.format(content_key, field_count)

                field = {
                    'name' : field_name,
                    'field' : form_field,
                }

                form_fields.append(field)

                if is_first == True:
                    is_first = False


            # optionally add empty field
            if max_number is None or field_count < max_number:
                # is_last is False
                is_last = True

                form_field = self.get_image_form_field(content_key, content_definition)
                
                form_field.is_first = is_first
                form_field.is_last = is_last
        
                field = {
                    'name' : content_key,
                    'field' : form_field,
                }
                
                form_fields.append(field)


        elif content_definition['type'] == 'image':
            current_image = None

            if instances:
                current_image = instances[0]
            
            form_field = self.get_image_form_field(content_key, content_definition, current_image)

            field = {
                'name' : content_key,
                'field' : form_field,
            }
            
            form_fields.append(field)


        
        elif content_definition['type'] == 'text':

            label = self._get_label(content_key, content_definition)

            field_kwargs = {
                'required' : False,
                'label' : label
            }

            widget = forms.Textarea
            if content_definition.get('widget', None) == 'TextInput':
                widget = forms.TextInput

            initial = ''

            if draft_contents and content_key in draft_contents:
                initial = draft_contents[content_key]
                                                
            field_kwargs.update({
                'widget' : widget,
                'initial' : initial,
            })
                                                
            form_field = forms.CharField(**field_kwargs)
            form_field.primary_locale_content = None

            if self.primary_locale_template_content.draft_contents:
                form_field.primary_locale_content = self.primary_locale_template_content.draft_contents.get(content_key, 'None')

            field = {
                'name' : content_key,
                'field' : form_field,
            }
            
            form_fields.append(field)


        return form_fields


    def get_image_form_field(self, content_key, content_definition, current_image=None):

        widget_attrs = self._get_widget_attrs(content_key, content_definition)

        label = self._get_label(content_key, content_definition)

        field_kwargs = {
            'required' : False,
            'label' : label
        }
        
        data_url = None
        delete_url = None

        if current_image:

            data_url_kwargs = {
                'content_image_id' : current_image.id,
            }

            data_url = reverse('manage_template_content_image', kwargs=data_url_kwargs)
            
            delete_kwargs = {
                'pk' : current_image.pk,
            }

            delete_url = reverse('delete_template_content_image', kwargs=delete_kwargs)

        else :
            if self.localized_template_content:
                ltc_content_type = ContentType.objects.get_for_model(self.localized_template_content)

                data_url_kwargs = {
                    'content_type_id' : ltc_content_type.id,
                    'object_id' : self.localized_template_content.id,
                    'image_type' : content_key
                }

                data_url = reverse('manage_template_content_image', kwargs=data_url_kwargs)
            
        widget_attrs['data-url'] = data_url  
        widget_attrs['accept'] = 'image/*'

        form_field = forms.ImageField(widget=forms.FileInput(widget_attrs), **field_kwargs)
        form_field.current_image = current_image

        form_field.licenced_url = data_url
        form_field.delete_url = delete_url

        return form_field   


    def _get_label(self, content_key, content_definition):
        fallback_label = label = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', content_key).capitalize()
        label = content_definition.get('label', fallback_label)
        return label

    def _get_widget_attrs(self, content_key, content_definition):

        widget_attrs = {
            'data-content-key' : content_key,
            'data-type' : content_definition['type'],
        }

        if content_definition['type'] == 'multi-images':
            widget_attrs.update({
                'multi' : True,
            })

        return widget_attrs



class ManageLocalizedTemplateContentForm(TemplateContentFormCommon):

    def __init__(self, app, template_content, localized_template_content=None, *args, **kwargs):

        language = kwargs.get('language', None)
        if localized_template_content:
            language = localized_template_content.language

        super().__init__(*args, **kwargs)

        self.localized_template_content = localized_template_content
        self.template_content = template_content

        self.layoutable_full_fields = set([])
        self.layoutable_simple_fields = set([])


        template_definition = self.template_content.draft_template.definition

        field_manager = TemplateContentFormFieldManager(app, self.template_content, self.localized_template_content)

        # content_key is the key in the json
        for content_key, content_definition in template_definition['contents'].items():

            instances = []

            if content_definition['type'] in ['image', 'multi-image']:
                if self.localized_template_content:
                    instances = self.localized_template_content.images(image_type=content_key).order_by('pk')


            form_fields = field_manager.get_form_fields(content_key, content_definition, instances)

            # get form fields for each content_id
            for field in form_fields:

                field['field'].content_definition = content_definition
                field['field'].content_key = content_key
                
                self.fields[field['name']] = field['field']

                self.fields[field['name']].language = language
                
                if content_definition.get('format', None) == 'layoutable-simple':
                    self.layoutable_simple_fields.add(field['name'])
                elif content_definition.get('format', None) == 'layoutable-full':
                    self.layoutable_full_fields.add(field['name'])



class TranslateTemplateContentForm(ManageLocalizedTemplateContentForm):

    pass