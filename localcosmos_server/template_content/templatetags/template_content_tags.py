from django.utils.html import format_html
from django import template
register = template.Library()

@register.simple_tag
def get_locale(localizeable_instance, language_code):
    return localizeable_instance.get_locale(language_code)


@register.simple_tag
def get_content(template_content, content_key, language_code):

    localized_template_content = template_content.get_locale(language_code)

    if localized_template_content:

        if content_key == 'draft_title':
            return localized_template_content.draft_title
        else:
            content = localized_template_content.draft_contents.get(content_key, None)
            if content:
                return format_html(content)
    
    return None