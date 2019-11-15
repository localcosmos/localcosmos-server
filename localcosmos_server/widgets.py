from django import forms
from django.forms.utils import flatatt
from django.template import loader, Context
from django.utils.encoding import (
    force_str, force_text
)
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.safestring import mark_safe

from django.forms.widgets import FileInput

from django.contrib.contenttypes.models import ContentType

from django.utils import translation

class ImageInputWithPreview(FileInput):

    template_name = 'localcosmos_server/widgets/image_input_with_preview.html'

    def __init__(self, *args, **kwargs):
        self.current_image = kwargs.pop('current_image', None)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        context['current_image'] = self.current_image

        return context


class CropImageInput(ImageInputWithPreview):
    template_name = 'localcosmos_server/widgets/crop_image_input.html'
    

class AjaxFileInput(FileInput):

    template_name = 'localcosmos_server/widgets/ajax_file_input.html'

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None) # if no url is given, the action="" of the form will be used
        self.delete_url_name = kwargs.pop('delete_url_name', None) # if no delete_url_name is given, no delete button will be shown
        self.instance = kwargs.pop('instance', None)
        self.extra_css_classes = kwargs.pop('extra_css_classes', '')
        super().__init__(*args, **kwargs)


    def get_context(self, name, value, attrs):

        attrs['data-url'] = self.url

        context = super().get_context(name, value, attrs)
        # context['widget'] is now available

        extra_context = {
            'instance' : self.instance,
            'delete_url_name' : self.delete_url_name,
            'extra_css_classes' : self.extra_css_classes,
            'url' : self.url,
        }

        if self.instance:
            extra_context['content_type'] = ContentType.objects.get_for_model(self.instance)

        context.update(extra_context)

        return context
    


class TwoStepFileInput(AjaxFileInput):

    template_name = 'localcosmos_server/widgets/two_step_file_input.html'


# for AppThemeImages
# delete_url instead of delete_url_name, no content_type/object_id pair possible
# in the template, image urls are prefixed with http
class TwoStepDiskFileInput(FileInput):

    template_name = 'localcosmos_server/widgets/app_theme_image_file_input.html'

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None) # if no url is given, the action="" of the form will be used
        self.delete_url = kwargs.pop('delete_url', None) # if no delete_url is given, no delete button will be shown
        self.instance = kwargs.pop('instance', None)
        self.extra_css_classes = kwargs.pop('extra_css_classes', '')
        super().__init__(*args, **kwargs)


    def get_context(self, name, value, attrs):

        attrs['data-url'] = self.url

        context = super().get_context(name, value, attrs)
        # context['widget'] is now available

        extra_context = {
            'instance' : self.instance,
            'delete_url' : self.delete_url,
            'extra_css_classes' : self.extra_css_classes,
            'url' : self.url,
        }

        context.update(extra_context)

        return context
    
