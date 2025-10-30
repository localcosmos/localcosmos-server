from django.utils.html import format_html
from django import template

from localcosmos_server.template_content.Templates import Template
from localcosmos_server.template_content.utils import get_preview_text

register = template.Library()

@register.simple_tag
def get_locale(localizeable_instance, language_code):
    return localizeable_instance.get_locale(language_code)


@register.simple_tag
def get_content(template_content, content_key, language_code, content_type='text'):

    localized_template_content = template_content.get_locale(language_code)

    if localized_template_content:

        if content_key == 'draft_title':
            return localized_template_content.draft_title
        else:
            if content_type == 'image':
                return 'image'
            else:
                content = localized_template_content.draft_contents.get(content_key, None)
                if content:
                    if isinstance(content, list):
                        return content
                    return format_html(content)
    
    return None

@register.simple_tag
def get_component_preview_text(localized_template_content, content_key, instance):
    component_template = localized_template_content.template_content.get_component_template(content_key)
    return get_preview_text(component_template, instance)


@register.simple_tag
def get_stream_item_preview_text(localized_template_content, stream_item):
    component_template = Template(localized_template_content.template_content.app, stream_item['templateName'], 'component')
    return get_preview_text(component_template, stream_item)


@register.simple_tag
def get_stream_item_icon(localized_template_content, stream_item):
    component_template = Template(localized_template_content.template_content.app, stream_item['templateName'], 'component')
    icon = component_template.definition.get('icon', None)

    return icon
