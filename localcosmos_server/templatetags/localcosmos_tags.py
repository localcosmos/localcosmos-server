from django.conf import settings
from django import template
register = template.Library()

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _
from django.urls import reverse

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm, TypedTaxonomicRestrictionForm
from localcosmos_server.models import TaxonomicRestriction

'''
    render taxonomic restrictions from app taxa
'''
def get_taxonomic_restriction_context(content, content_type, restrictions, taxon_search_url, typed):
    
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
        'form': form_class(**form_kwargs),
        'typed': typed,
        'restrictions': restrictions,
        'content' : content,
        'content_type' : content_type,
    }
    return context

    
@register.inclusion_tag('localcosmos_server/taxonomic_restrictions_form.html')
def render_app_taxonomic_restriction(app, content, typed=None):

    taxon_search_url = reverse('search_app_taxon', kwargs={'app_uid':app.uid})

    content_type = ContentType.objects.get_for_model(content)
    restrictions = TaxonomicRestriction.objects.filter(
        content_type=content_type,
        object_id=content.id,
    )

    context = get_taxonomic_restriction_context(content, content_type, restrictions, taxon_search_url, typed)
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
