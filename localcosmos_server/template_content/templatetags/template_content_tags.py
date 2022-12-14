from django import template
register = template.Library()

from localcosmos_server.template_content.models import LocalizedTemplateContent

@register.simple_tag
def get_template_content_locale(template_content, language):
    return LocalizedTemplateContent.objects.filter(template_content=template_content, language=language).first()