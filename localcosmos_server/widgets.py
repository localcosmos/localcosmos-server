from django import forms
from django.forms.utils import flatatt
from django.template import loader, Context
from django.utils.encoding import (
    force_str, force_text
)
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.safestring import mark_safe

from django.forms.widgets import FileInput, HiddenInput

from django.contrib.contenttypes.models import ContentType

from django.utils import translation

class ImageInputWithPreview(FileInput):

    template_name = 'localcosmos_server/widgets/image_input_with_preview.html'

    def __init__(self, *args, **kwargs):
        self.current_image = kwargs.pop('current_image', None)
        self.restrictions = kwargs.pop('restrictions', {})
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):

        accept = 'image/*'
        
        # accept=".png, .jpg"

        if self.restrictions and 'file_type' in self.restrictions:

            accept = ''

            for file_type in self.restrictions['file_type']:

                if len(accept) > 0:
                    accept = '{0}, '.format(accept)

                accept = '{0}.{1}'.format(accept, file_type)

        attrs['accept'] = accept

        context = super().get_context(name, value, attrs)

        context['current_image'] = self.current_image
        context['restrictions'] = self.restrictions

        return context


class CropImageInput(ImageInputWithPreview):
    template_name = 'localcosmos_server/widgets/crop_image_input.html'


import json
class HiddenJSONInput(HiddenInput):
    
    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        if value == '' or value is None:
            return None
        
        return json.dumps(value)
    

class AjaxFileInput(FileInput):

    template_name = 'localcosmos_server/widgets/ajax_file_input.html'

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None) # if no url is given, the action="" of the form will be used
        self.delete_url_name = kwargs.pop('delete_url_name', None) # if no delete_url_name is given, no delete button will be shown
        self.instance = kwargs.pop('instance', None)
        self.extra_css_classes = kwargs.pop('extra_css_classes', '')
        self.restrictions = kwargs.pop('restrictions', {})
        self.image_container_id = kwargs.pop('image_container_id', None)
        super().__init__(*args, **kwargs)


    def get_context(self, name, value, attrs):

        attrs['data-url'] = self.url

        context = super().get_context(name, value, attrs)
        # context['widget'] is now available

        ratio = None
        if self.restrictions:

            if 'ratio' in self.restrictions:

                ratio = self.restrictions['ratio']

                absolute_width = 12 #rem
                absolute_height = 12

                ratio_list = ratio.split(':')
                width = int(ratio_list[0])
                height = int(ratio_list[1])

                if width > height:
                    factor = width/height
                    absolute_width = int(absolute_width * factor)

                else:
                    factor = height/width
                    absolute_height = int(absolute_height * factor)

                ratio = {
                    'verbose' : ratio,
                    'absolute_width' : absolute_width,
                    'absolute_height' : absolute_height,
                }

        extra_context = {
            'instance' : self.instance,
            'delete_url_name' : self.delete_url_name,
            'extra_css_classes' : self.extra_css_classes,
            'url' : self.url,
            'ratio' : ratio,
            'restrictions' : self.restrictions,
            'image_container_id' : self.image_container_id,
        }

        if self.instance:
            extra_context['content_type'] = ContentType.objects.get_for_model(self.instance)

        context.update(extra_context)

        return context
    


class TwoStepFileInput(AjaxFileInput):

    template_name = 'localcosmos_server/widgets/two_step_file_input.html'