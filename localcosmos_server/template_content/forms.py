from django.conf import settings
from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import (NAVIGATION_LINK_NAME_MAX_LENGTH, TemplateContent, Navigation, NavigationEntry,
                     LocalizedTemplateContent, NavigationEntry, LocalizedNavigationEntry)

from .Templates import Template, Templates

from .fields import ComponentField, StreamField
from .widgets import (ContentWithPreviewWidget, FileContentWidget, TextareaContentWidget, TextContentWidget,
                      StreamContentWidget)

from .utils import get_preview_text

from django.contrib.auth import get_user_model

from localcosmos_server.forms import LocalizeableForm

from localcosmos_server.template_content.utils import get_component_image_type

import re

User = get_user_model()


class TemplateContentFormCommon(LocalizeableForm):

    draft_title = forms.CharField(label=_('Title'))

    localizeable_fields = ['draft_title']


class CreateTemplateContentForm(TemplateContentFormCommon):
    
    template_name = forms.ChoiceField(label =_('Template'))

    def __init__(self, app, *args, **kwargs):

        self.app = app
        self.assignment = kwargs.pop('assignment', None)
        
        super().__init__(*args, **kwargs)

        # load the template_choices
        templates = Templates(self.app, 'page')
        available_templates = templates.get_all_templates()

        choices = []

        if available_templates:
            for template_name, template in available_templates.items():
                choice = (template_name, template.definition['templateName'])
                choices.append(choice)
        self.fields['template_name'].choices = choices
        

    def clean(self):

        if self.assignment:
            assigned_template_content_exists = TemplateContent.objects.filter(app=self.app,
                                                                              assignment=self.assignment).exists()

            if assigned_template_content_exists == True:
                raise forms.ValidationError('A template content for "{0}" already exists'.format(self.assignment))


# translations initially do not supply a localized_template_content? - change this!!
class TemplateContentFormFieldManager:

    manage_content_image_url_name = 'manage_template_content_image'
    delete_content_image_url_name = 'delete_template_content_image'

    def __init__(self, app, template_content, localized_template_content):
        self.app = app
        self.template_content = template_content
        self.localized_template_content = localized_template_content
        self.primary_locale_template_content = template_content.get_locale(app.primary_language)

    # allowMultiple=False
    def get_instance(self, content_key, content_type):
        
        instance = None
        
        if self.localized_template_content:
            if content_type == 'image':
                image_type = self._get_image_type(content_key)
                instance = self.localized_template_content.image(image_type=image_type)

            elif content_type in ['component', 'text', 'templateContentLink'] and self.localized_template_content.draft_contents:
                instance = self.localized_template_content.draft_contents.get(content_key, None)
        
        return instance
    
    # allowMultiple=True
    def get_instances(self, content_key, content_type):

        instances = []

        if self.localized_template_content:
            if content_type == 'image':
                image_type = self._get_image_type(content_key)
                instances = list(self.localized_template_content.images(image_type=image_type).order_by('pk'))

            elif content_type in ['component', 'text', 'templateContentLink', 'stream'] and self.localized_template_content.draft_contents:
                instances = self.localized_template_content.draft_contents.get(content_key, [])

        return instances


    def get_primary_locale_content(self, content_key):
        content = None
        if self.primary_locale_template_content.draft_contents:
            content = self.primary_locale_template_content.draft_contents.get(content_key, None)
        return content


    def _add_primary_locale_content_to_form_field(self, form_field, content_key):

        form_field.primary_locale_content = None

        if self.primary_locale_template_content.draft_contents:
            form_field.primary_locale_content = self.get_primary_locale_content(content_key)

        return form_field


    '''
        {
            "title": "Sample page",
            "templateName": "Sample",
            "templatePath": "/template_content/page/sample/sample.html",
            "version": 1,
            "contents": {
                "stream": [
                    {
                        "templateName": "Video",
                        "type": "component",
                        (...other component fields...)
                    }
                ]
            }
        }
    '''
    def get_form_fields(self, content_key, content_definition):
        
        form_fields = []
        
        content_type = content_definition['type']
        allow_multiple = content_definition.get('allowMultiple', False)

        field_getter_name = '_get_{0}_form_field'.format(content_type)
        field_getter = getattr(self, field_getter_name)

        if content_type != 'stream' and allow_multiple == True:
            instances = self.get_instances(content_key, content_definition['type'])
            max_number = content_definition.get('maxNumber', None)

            is_first = True
            is_last = False
            field_count = 0

            for instance in instances:
                
                field_count += 1
                if field_count == max_number:
                    is_last = True

                field_name = '{0}-{1}'.format(content_key, field_count)

                form_field = field_getter(content_key, content_definition, instance)
                form_field.allow_multiple = True

                form_field.is_first = is_first
                form_field.is_last = is_last

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

                empty_form_field = field_getter(content_key, content_definition)
                empty_form_field.allow_multiple = True
                
                empty_form_field.is_first = is_first
                empty_form_field.is_last = is_last
        
                empty_field = {
                    'name' : content_key,
                    'field' : empty_form_field,
                }
                
                form_fields.append(empty_field)


        else:
            
            instance = self.get_instance(content_key, content_definition['type'])

            # how could it be a list?
            if isinstance(instance, list) and len(instance) > 0:
                instance = instance[0]

            form_field = field_getter(content_key, content_definition, instance)
            form_field.allow_multiple = False

            field = {
                'name' : content_key,
                'field' : form_field,
            }
            
            form_fields.append(field)

        return form_fields

    

    def _get_label(self, content_key, content_definition):
        fallback_label = label = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', content_key).capitalize()
        label = content_definition.get('label', fallback_label)
        return label


    def _get_required(self, content_definition):
        return False
    
    def _get_common_widget_attrs(self, content_key, content_definition, instance):

        widget_attrs = {
            'content_key' : content_key,
            'content_type' : content_definition['type'],
            'instance': instance,
            'definition': content_definition,
        }

        return widget_attrs



    def _get_common_field_kwargs(self, content_key, content_definition):

        label = self._get_label(content_key, content_definition)
        help_text = content_definition.get('helpText', None)
        required = self._get_required(content_definition)

        field_kwargs = {
            'required' : required,
            'label' : label,
            'help_text': help_text,
        }

        return field_kwargs


    def _get_image_type(self, content_key):
        return content_key

    def _get_image_form_field(self, content_key, content_definition, current_image=None):

        image_type = self._get_image_type(content_key)

        widget_attrs = self._get_common_widget_attrs(content_key, content_definition, current_image)

        field_kwargs = self._get_common_field_kwargs(content_key, content_definition)
        
        data_url = None
        delete_url = None

        if current_image:

            data_url_kwargs = {
                'app_uid' : self.app.uid,
                'content_image_id' : current_image.id,
            }

            data_url = reverse(self.manage_content_image_url_name, kwargs=data_url_kwargs)
            
            delete_kwargs = {
                'app_uid': self.app.uid,
                'pk' : current_image.pk,
            }

            delete_url = reverse(self.delete_content_image_url_name, kwargs=delete_kwargs)

        else :
            if self.localized_template_content:
                
                ltc_content_type = ContentType.objects.get_for_model(self.localized_template_content)

                data_url_kwargs = {
                    'app_uid' : self.app.uid,
                    'content_type_id' : ltc_content_type.id,
                    'object_id' : self.localized_template_content.id,
                    'image_type' : image_type
                }

                data_url = reverse(self.manage_content_image_url_name, kwargs=data_url_kwargs)
            
        widget_attrs['data_url'] = data_url
        widget_attrs['delete_url'] = delete_url
        widget_attrs['accept'] = 'image/png, image/webp, image/jpeg'

        widget = FileContentWidget(widget_attrs)
        form_field = forms.ImageField(widget=widget, **field_kwargs)

        # add primary locale ServerContentImage as form_field.primary_locale_content
        allow_multiple = content_definition.get('allowMultiple', False)
        if allow_multiple == True:
            primary_locale_images = list(self.primary_locale_template_content.images(image_type=content_key).order_by('pk'))
        else:
            primary_locale_images = self.primary_locale_template_content.images(image_type=content_key).order_by('pk').last()

        form_field.primary_locale_content = primary_locale_images

        return form_field

    def _get_text_form_field(self, content_key, content_definition, instance=None):

        field_kwargs = self._get_common_field_kwargs(content_key, content_definition)

        widget_name = content_definition.get('widget', None)
        
        widget = TextareaContentWidget
        field_class = forms.CharField
        
        if widget_name == 'TextInput':
            widget = TextContentWidget
        elif widget_name == 'Select':
            choices_definition = content_definition.get('choices', [])
            choices = [(option, option) for option in choices_definition]
            field_kwargs['choices'] = choices
            widget = forms.Select
            field_class = forms.ChoiceField
            
        initial = ''
        if instance:
            initial = instance
                                            
        field_kwargs.update({
            'widget' : widget,
            'initial' : initial,
        })
                                            
        form_field = field_class(**field_kwargs)

        form_field = self._add_primary_locale_content_to_form_field(form_field, content_key)
        
        return form_field

    
    def _get_component_form_field(self, content_key, content_definition, instance=None):

        component_template = self.template_content.get_component_template(content_key)

        field_kwargs = self._get_common_field_kwargs(content_key, content_definition)

        widget_attrs = self._get_common_widget_attrs(content_key, content_definition, instance)

        data_url_kwargs = {
            'app_uid': self.app.uid,
            'localized_template_content_id': self.localized_template_content.pk,
            'content_key': content_key,
        }

        delete_url = None
        preview_text = None

        if instance:
            data_url_kwargs['component_uuid'] = instance['uuid']
            delete_url = reverse('delete_component', kwargs=data_url_kwargs)

            preview_text = get_preview_text(component_template, instance)

        if instance:
            data_url = reverse('manage_component', kwargs=data_url_kwargs)
        else:
            data_url = reverse('add_component', kwargs=data_url_kwargs)

        widget_attrs['data_url'] = data_url
        widget_attrs['delete_url'] = delete_url
        widget_attrs['preview_text'] = preview_text 

        widget = ContentWithPreviewWidget(widget_attrs)

        initial = ''
                                            
        field_kwargs.update({
            'widget' : widget,
            'initial' : initial,
        })
                                            
        form_field = ComponentField(**field_kwargs)

        form_field = self._add_primary_locale_content_to_form_field(form_field, content_key)

        return form_field
    
    
    def _get_stream_form_field(self, content_key, content_definition, instance=None):
        
        field_kwargs = self._get_common_field_kwargs(content_key, content_definition)
        
        widget = StreamContentWidget(self.app, self.localized_template_content, content_key, content_definition)
        
        field_kwargs.update({
            'widget' : widget,
        })
        
        form_field = StreamField(**field_kwargs)
        
        return form_field


    def _get_templateContentLink_form_field(self, content_key, content_definition, instance=None):

        field_kwargs = self._get_common_field_kwargs(content_key, content_definition)

        widget_attrs = self._get_common_widget_attrs(content_key, content_definition, instance)

        widget = forms.Select(widget_attrs)

        queryset = LocalizedTemplateContent.objects.filter(published_version__isnull=False)

        initial = None

        if instance:
            initial = LocalizedTemplateContent.objects.filter(pk=instance['pk']).first()

        field_kwargs.update({
            'queryset': queryset,
            'widget' : widget,
            'initial' : initial,
        })

        form_field = forms.ModelChoiceField(**field_kwargs)

        form_field = self._add_primary_locale_content_to_form_field(form_field, content_key)

        return form_field



class ComponentFormFieldManager(TemplateContentFormFieldManager):

    manage_content_image_url_name = 'manage_component_image'
    delete_content_image_url_name = 'delete_component_image'

    # component_uuid can be None for new components
    def __init__(self, app, template_content, localized_template_content, component_key, component_uuid, component={}):
        self.app = app
        self.template_content = template_content
        self.localized_template_content = localized_template_content
        self.primary_locale_template_content = template_content.get_locale(app.primary_language)
        self.component_key = component_key
        self.component_uuid = component_uuid
        self.component = component

    # component_key:uuid:content_key
    def _get_image_type(self, content_key):
        return get_component_image_type(self.component_key, self.component_uuid, content_key)


    def get_instance(self, content_key, content_type):
        
        instance = None

        if self.component:
            
            if content_type == 'image':
                image_type = self._get_image_type(content_key)
                instance = self.localized_template_content.image(image_type=image_type)

            elif content_type in ['component', 'text', 'templateContentLink']:
                instance = self.component.get(content_key, None)

        return instance
    
        
    def get_instances(self, content_key, content_type):

        instances = []

        if self.component:
            
            if content_type == 'image':
                image_type = self._get_image_type(content_key)
                instances = list(self.localized_template_content.images(image_type=image_type).order_by('pk'))

            elif content_type in ['component', 'text', 'templateContentLink']:
                instances = self.component.get(content_key, [])

        return instances

    def get_primary_locale_content(self, content_key):
        return [] #self.primary_locale_template_content.draft_contents[self.component_key].get(content_key, 'None')

    def _get_required(self, content_definition):
        return content_definition.get('required', False)



class ManageLocalizedTemplateContentForm(TemplateContentFormCommon):

    def __init__(self, app, template_content, localized_template_content=None, *args, **kwargs):

        super().__init__(*args, **kwargs)
        
        self.language = kwargs.get('language', None)
        if localized_template_content:
            self.language = localized_template_content.language

        self.app = app
        self.template_content = template_content
        self.localized_template_content = localized_template_content

        self.layoutable_full_fields = set([])
        self.layoutable_simple_fields = set([])

        self.set_template_definition()

        if self.localized_template_content:
            self.set_form_fields()

    def set_template_definition(self):
        self.template_definition = self.template_content.draft_template.definition


    def get_form_field_manager(self):
        return TemplateContentFormFieldManager(self.app, self.template_content, self.localized_template_content)


    def set_form_fields(self):

        field_manager = self.get_form_field_manager()

        # content_key is the key in the json
        for content_key, content_definition in self.template_definition['contents'].items():

            form_fields = field_manager.get_form_fields(content_key, content_definition)

            # get form fields for each content_id
            for field_definition in form_fields:
                
                field = field_definition['field']
                field_name = field_definition['name']

                field.content_definition = content_definition
                field.content_key = content_key
                field.language = self.language
                
                self.fields[field_name] = field
                
                if content_definition.get('format', None) == 'layoutable-simple':
                    self.layoutable_simple_fields.add(field_name)
                elif content_definition.get('format', None) == 'layoutable-full':
                    self.layoutable_full_fields.add(field_name)


class ManageComponentForm(ManageLocalizedTemplateContentForm):

    uuid = forms.UUIDField(widget=forms.HiddenInput)

    localizeable_fields = []

    def __init__(self, app, template_content, localized_template_content, content_key, component_template_name, component=None, *args, **kwargs):
        initial = kwargs.get('initial', {})
        
        if 'uuid' not in initial:
            raise ValueError("initial['uuid] is required")

        self.component_template_name = component_template_name


        self.content_key = content_key
        self.component = component
        
        super().__init__(app, template_content, localized_template_content, *args, **kwargs)

        self.fields.pop('draft_title')
        
    def set_template_definition(self):
        # load the component template
        component_template = Template(self.app, self.component_template_name, 'component')
        self.template_definition = component_template.definition

    def get_form_field_manager(self):
        component_uuid = self.initial['uuid']
        return ComponentFormFieldManager(self.app, self.template_content, self.localized_template_content, self.content_key,
                                        component_uuid, self.component)
        
    def add_prefix(self, field_name):
        # look up field name; return original if not found
        field_name = '{0}_{1}'.format(self.content_key, field_name)
        return super().add_prefix(field_name)



class TranslateTemplateContentForm(ManageLocalizedTemplateContentForm):
    pass


class ManageNavigationForm(LocalizeableForm):

    name = forms.CharField(max_length=355)
    navigation_type = forms.ChoiceField()

    localizeable_fields = ['name']

    def __init__(self, app, *args, **kwargs):
        self.app = app
        self.navigation = kwargs.pop('navigation', None)
        super().__init__(*args, **kwargs)
        # read navigation_type choices from frontend
        frontend_settings = app.get_settings()
        navigations = {}
        
        if 'templateContent' in frontend_settings and 'navigations' in frontend_settings['templateContent']:
            navigations = frontend_settings['templateContent']['navigations']

        choices = []

        for navigation_type, definition in navigations.items():

            if settings.LOCALCOSMOS_PRIVATE == True and definition.get('offline', False) == True:
                continue

            choice = (navigation_type, definition['name'])
            choices.append(choice)

        self.fields['navigation_type'].choices = choices


    def clean_navigation_type(self):
        
        navigation_type = self.cleaned_data['navigation_type']

        exists = Navigation.objects.filter(app=self.app, navigation_type=navigation_type).first()
        if exists and exists != self.navigation:
            raise forms.ValidationError(_('A navigation of type %(navigation_type)s already exists') % {
                'navigation_type': navigation_type
            })

        return navigation_type



# a form for selecting a template content as a navigation entry
# maximum supported levels are 3
class ManageNavigationEntryForm(LocalizeableForm):

    link_name = forms.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH)
    template_content = forms.ModelChoiceField(label=_('Page'), queryset=TemplateContent.objects.all(),
        required=False)
    parent = forms.ModelChoiceField(queryset=NavigationEntry.objects.all(), required=False)
    
    localizeable_fields = ['link_name']

    def __init__(self, navigation, *args, **kwargs):

        self.navigation_entry = kwargs.pop('navigation_entry', None)
        self.max_levels = navigation.settings.get('maxLevels', 1)

        super().__init__(*args, **kwargs)
        self.fields['template_content'].queryset = TemplateContent.objects.filter(app=navigation.app)

        if self.max_levels == 1:
            parent_queryset = NavigationEntry.objects.none()
            
        elif self.max_levels == 2:
            parent_queryset = NavigationEntry.objects.filter(navigation=navigation, parent=None)
            
        else:
            parent_q = Q(parent=None)
            grandparent_q = Q(parent__parent=None)
            parent_queryset = NavigationEntry.objects.filter(Q(navigation=navigation), parent_q | grandparent_q)

        if self.navigation_entry:
            exclude_pks = [self.navigation_entry.pk]
            #parent = self.navigation_entry.parent
            #if parent:
            #    exclude_pks.append(parent.pk)

            for entry in self.navigation_entry.descendants:
                exclude_pks.append(entry.pk)
                
                    
            parent_queryset = parent_queryset.exclude(pk__in=exclude_pks)

        self.fields['parent'].queryset = parent_queryset



class TranslateNavigationForm(LocalizeableForm):

    name = forms.CharField(max_length=355, label=_('Name of the navigation'))
    localizeable_fields = ['name']
    
    def __init__(self, app, navigation, *args, **kwargs):
        self.navigation = navigation
        self.primary_language = app.primary_language
        self.language = kwargs['language']
        self.primary_locale_navigation = navigation.get_locale(self.primary_language)
        self.navigation_entries = NavigationEntry.objects.filter(navigation=self.navigation)

        self.localized_navigation = navigation.get_locale(self.language)
        super().__init__(*args, **kwargs)

        self.set_form_fields()


    def set_form_fields(self):
        
        self.fields['name'].primary_locale_text = self.primary_locale_navigation.name

        for navigation_entry in self.navigation_entries:

            primary_locale_navigation_entry = navigation_entry.get_locale(self.primary_language) 
            localized_navigation_entry = navigation_entry.get_locale(self.language)
            widget = forms.TextInput

            initial = ''
            if localized_navigation_entry:
                initial = localized_navigation_entry.link_name

            label = '{0}'.format(primary_locale_navigation_entry.link_name)
                                                
            field_kwargs = {
                'widget' : widget,
                'initial' : initial,
                'label': label,
                'required': False
            }
                                                
            form_field = forms.CharField(**field_kwargs)
            form_field.primary_locale_text = primary_locale_navigation_entry.link_name
            form_field.language = self.language
            form_field.navigation_entry = navigation_entry

            field_name = 'ne-{0}'.format(navigation_entry.id)

            self.fields[field_name] = form_field