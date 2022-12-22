from django.conf import settings
from django import template
register = template.Library()

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _
from django.urls import reverse

from localcosmos_server.utils import get_taxon_search_url
from localcosmos_server.taxonomy.forms import AddSingleTaxonForm, TypedTaxonomicRestrictionForm
from localcosmos_server.models import TaxonomicRestriction
from localcosmos_server.template_content.models import TemplateContent


'''
    render taxonomic restrictions from app taxa
'''
def get_taxonomic_restriction_context(app, content, content_type, restrictions, taxon_search_url, typed, action_url):
    
    form_class = AddSingleTaxonForm
    if typed == 'typed':
        form_class = TypedTaxonomicRestrictionForm
    
    # sometimes more than one taxonomic restriciont form can be on the page
    prefix = '{0}-{1}'.format(content_type.id, content.id)

    form_kwargs = {
        'taxon_search_url' : taxon_search_url,
        'prefix' : prefix,
    }

    context = {
        'app' : app,
        'form': form_class(**form_kwargs),
        'typed': typed,
        'restrictions': restrictions,
        'content' : content,
        'content_type' : content_type,
        'action_url' : action_url,
    }
    return context

# combined restrictions for app_kit and localcosmos_server
@register.inclusion_tag('localcosmos_server/taxonomy/taxonomic_restrictions.html')
def render_taxonomic_restriction(app, content, typed=None):

    content_type = ContentType.objects.get_for_model(content)

    url_kwargs = {
        'content_type_id' : content_type.id,
        'object_id' : content.id,
    }

    if typed == 'typed':
        url_kwargs['typed'] = 'typed'


    if settings.LOCALCOSMOS_PRIVATE == True or content.__class__ == TemplateContent:
        RestrictionModel = TaxonomicRestriction
        url_kwargs['app_uid'] = app.uid
        action_url = reverse('manage_app_taxonomic_restrictions', kwargs=url_kwargs)
    else:
        from app_kit.generic import AppContentTaxonomicRestriction
        RestrictionModel = AppContentTaxonomicRestriction
        action_url = reverse('add_taxonomic_restriction',  kwargs=url_kwargs)

    taxon_search_url = get_taxon_search_url(app, content)
    
    restrictions = RestrictionModel.objects.filter(
        content_type=content_type,
        object_id=content.id,
    )

    context = get_taxonomic_restriction_context(app, content, content_type, restrictions, taxon_search_url, typed, action_url)
    return context


'''
    bootstrap
'''
@register.inclusion_tag('localcosmos_server/bootstrap_form.html')
def render_bootstrap_form(form):
    return {'form':form}


@register.inclusion_tag('localcosmos_server/bootstrap_field.html')
def render_bootstrap_field(field):
    return {'field':field}

@register.filter
def field_class(field):
    return field.__class__.__name__


@register.filter
def widget_class(widget):
    return widget.__class__.__name__


@register.filter
def class_name(obj):
    return obj.__class__.__name__


import json
from django.utils.safestring import mark_safe
@register.filter
def as_json(obj):
    return mark_safe(json.dumps(obj))


@register.filter
def ctype_id(identifier):
    if isinstance(identifier, str):
        app_label, model_name = identifier.split(".")
        ctype = ContentType.objects.get(app_label=app_label.lower(), model=model_name.lower())
    else:
        ctype = ContentType.objects.get_for_model(identifier)
    return ctype.id


@register.filter
def ctype_name(content_type_id):
    ctype = ContentType.objects.get(pk=content_type_id)
    return _(ctype.model_class()._meta.verbose_name)


@register.filter
def modelname(Model):
    return Model._meta.verbose_name


@register.filter
def classname(instance):
    return instance.__class__.__name__


from rest_framework.renderers import HTMLFormRenderer

@register.simple_tag
def render_serializer_form(serializer, template_pack=None):
    style = {'template_pack': template_pack} if template_pack else {}
    renderer = HTMLFormRenderer()
    return renderer.render(serializer.data, None, {'style': style})

@register.simple_tag
def render_serializer_field(field, style):
    renderer = style.get('renderer', HTMLFormRenderer())
    return renderer.render_field(field, style)

@register.simple_tag(takes_context=True)
def get_app_locale(context, key):
    language = context['request'].LANGUAGE_CODE
    return context['request'].app.get_locale(key, language)


@register.simple_tag
def content_image_url(instance, image_type):
    content_image = instance.image(image_type)
    return content_image.image_url()