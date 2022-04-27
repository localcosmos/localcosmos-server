from django import forms
from django.conf import settings

from django.utils.translation import gettext as _

from .models import microcontent_category_model_map

import os, json

"""
    CMSTagObject is an object created from a template tag
    - currently only reads draft models
    - the templatetag can allow multiple instances of CMSObjects
"""
class CMSTag:

    def __init__(self, app, template_content, microcontent_category, microcontent_type, *args, **kwargs):

        self.app = app
        self.template_content = template_content
        
        self.microcontent_category = microcontent_category
        self.microcontent_type = microcontent_type
        self.args = list(args)

        # unlocalized model
        self.Model = self._get_model(microcontent_category)

        self.multi = False
        self.min_num = kwargs.get('min', 0)
        self.max_num = kwargs.get('max', None)

        self.is_translatable = True

        # translatable images have their own microcontent_category 
        if self.microcontent_category in ['image', 'images']:
            self.is_translatable = False
        
        if 'multi' in args:
            self.multi = True
            
        elif self.microcontent_category in ['images', 'microcontents']:
            self.multi = True
            self.args.append('multi')


    def _get_model(self, microcontent_category):
        Model = microcontent_category_model_map[microcontent_category]['draft']
        return Model
    
    """
    return a form field instance with an cms object attached to it
    """

    def _get_widget_attrs(self):
        widget_attrs = {
            'data-microcontentcategory' : self.microcontent_category,
            'data-microcontenttype' : self.microcontent_type,
            'data-type' : '{0}-{1}'.format(self.microcontent_category, self.microcontent_type),
        }

        return widget_attrs


    '''
    return an usaved instance of self.Model. self.Model is e.g. DraftTextMicroContent or DraftImageMicrocontent and
    not the Localized Model
    '''
    def get_empty_localized_instance(self):
        LocaleModel = self.Model().get_locale_model() 
        instance = LocaleModel()
        return instance

    '''
    return the form fields
    a) for the primary language
    b) for the translation language
        - the localized fields do not exist at first, but the unlocalized instance is needed to fetch the content
          in the primary language
    '''
    def form_fields(self, language, template_content=None, **kwargs):

        for_translation = kwargs.get('for_translation', False)

        # images are currently not translatable -> self.is_translatable == False for images
        if for_translation == True and self.is_translatable == False:
            return []

        form_fields = []

        widget_attrs = self._get_widget_attrs()

        if self.multi:

            # the first of multiple fields
            is_first = True
            is_last = False

            field_count = 0

            # first, fetch all language independant instances
            meta_instances = self.Model.objects.filter(template_content=template_content,
                                            microcontent_type=self.microcontent_type).order_by('position', 'pk')

            # there can be a meta instance without a matching locale, in the case of translation
            for meta_instance in meta_instances:

                localized_instance = meta_instance.get_localized(language)
                if not localized_instance:
                    localized_instance = self.get_empty_localized_instance()

                field_count += 1

                # add an empty field if max_num not reached yet
                if self.max_num is None or self.max_num <= field_count:

                    # check if this is the last field
                    if self.max_num is not None and field_count == self.max_num:
                        is_last = True

                # this field_name is used if no instance with pk is given
                field_name = '{0}-{1}'.format(self.microcontent_type, field_count)
                field = self._create_field(language, meta_instance, localized_instance, widget_attrs,
                                           is_first=is_first, is_last=is_last, field_name=field_name)
                form_fields.append(field)
                
                is_first = False
                    

            # add multi-value field for content / multi-image-field for images
            # there is always only one blank field - except if for_translation == True
            if (self.max_num is None or field_count < self.max_num) and for_translation == False:
                # is_last is False
                is_last = True

                # append attrs to the widget
                widget_attrs.update({
                    'multi' : True,
                })

        
                empty_localized_instance = self.get_empty_localized_instance()
                empty_meta_instance = self.Model()
                    
                field = self._create_field(language, empty_meta_instance, empty_localized_instance, widget_attrs,
                                           is_first=is_first, is_last=is_last)
                
                form_fields.append(field)
                is_first = False

        # non-multi fields
        else:
            # check if the cms object already exists, if so, use initial for the field
            meta_instance = self.Model.objects.filter(template_content=template_content,
                                                      microcontent_type=self.microcontent_type).first()
            
            if meta_instance:
                localized_instance = meta_instance.get_localized(language)
                if not localized_instance:
                    localized_instance = self.get_empty_localized_instance()
            else:
                localized_instance = self.get_empty_localized_instance()
                meta_instance = self.Model()
                
            field = self._create_field(language, meta_instance, localized_instance, widget_attrs)
            form_fields.append(field)

        return form_fields


    def create_empty_field(self, language):
        localized_instance = self.get_empty_localized_instance()
        meta_instance = self.Model()
        widget_attrs = self._get_widget_attrs()

        return self._create_field(language, meta_instance, localized_instance, widget_attrs)

    # multi fields also pass is_first/is_last in kwargs
    def _create_field(self, language, meta_instance, localized_instance, widget_attrs={}, **kwargs):

        widget_attrs = widget_attrs.copy()

        if localized_instance.pk:
            field_name = 'pk-{0}-{1}'.format(localized_instance.microcontent.pk, self.microcontent_type)
            widget_attrs['data-localized-pk'] = localized_instance.pk
            widget_attrs['data-meta-pk'] = localized_instance.microcontent.pk
        else:
            # if is-multi is set, especially for translations, a field_name with a counter suffix like 'type-1'
            # is provided
            field_name = kwargs.get('field_name', self.microcontent_type)

        field_kwargs = self._get_field_kwargs(language, localized_instance=localized_instance)
        field_kwargs['label'] = _(self.microcontent_type)

        # required for image uploads
        widget_attrs['language'] = language

        form_field = meta_instance.get_form_field(self.app, self.template_content, widget_attrs, *self.args,
                                                  **field_kwargs)

        form_field.meta_instance = meta_instance
        form_field.localized_instance = localized_instance
            
        form_field.cms_object = CMSObject(self.Model, self.microcontent_category, self.microcontent_type,
                self.multi, self.min_num, self.max_num, meta_instance, localized_instance, *self.args, **kwargs)

        field = {
            'field' : form_field,
            'name' : field_name, 
        }

        return field
        
    
    # for translations, language is necessary
    def _get_field_kwargs(self, language, localized_instance=None):
        kwargs = {
            'required' : False, # fields are only required when publishing
        }

        if localized_instance is not None and localized_instance.pk:
            kwargs['initial'] = localized_instance.get_content()

        return kwargs           



"""
    content_categories are template_content(TemplateContent), text_microcontent(MicroContent), image_microcontent(ContentImage)
"""

class CMSObject:

    def __init__(self, Model, microcontent_category, microcontent_type, multi, min_num, max_num, meta_instance,
                 localized_instance, *args, **kwargs):
        
        self.microcontent_category = microcontent_category
        self.microcontent_type = microcontent_type
        self.args = args        
        self.Model = microcontent_category_model_map[microcontent_category]['draft']
        self.multi = multi
        self.min_num = min_num
        self.max_num = max_num
        self.is_file = 'image' in self.microcontent_category
        self.meta_instance = meta_instance
        self.localized_instance = localized_instance
        self.kwargs = kwargs


class Theme:

    def __init__(self, theme_name):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.dir_path = os.path.join(dir_path, "themes", theme_name)

        if not os.path.isdir(self.dir_path):
            raise FileNotFoundError("The theme %s could not be found." % theme_name)

        settings_file_path = os.path.join(self.dir_path, "settings.json")

        if not os.path.isfile(settings_file_path):
            raise FileNotFoundError("settings file for theme %s could not be found." % theme_name)

        with open(settings_file_path, "r") as f:
            self.settings = json.load(f)
        
