from django.utils.html import format_html
from django import template
register = template.Library()

from localcosmos_server.template_content.models import LocalizedTemplateContent

@register.simple_tag
def get_template_content_locale(template_content, language):
    return LocalizedTemplateContent.objects.filter(template_content=template_content, language=language).first()


@register.simple_tag
def get_content(template_content, content_key, language_code):

    localized_template_content = template_content.get_locale(language_code)

    if localized_template_content:

        if content_key == 'draft_title':
            return localized_template_content.draft_title
        elif content_key == 'draft_navigation_link_name':
            return localized_template_content.draft_navigation_link_name
        else:
            content = localized_template_content.draft_contents.get(content_key, None)
            if content:
                return format_html(content)
    
    return None