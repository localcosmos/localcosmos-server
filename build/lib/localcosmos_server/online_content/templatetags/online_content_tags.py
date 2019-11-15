from django.conf import settings
from django import template
register = template.Library()

from django.template import loader, Context

from localcosmos_server.online_content.models import (TemplateContent, LocalizedTemplateContent,
                                                      microcontent_category_model_map)

from django.db.models import Q

'''
    get_content_by_type
    - get content by TemplateContent.template_type
    - app object is needed
'''
@register.simple_tag(takes_context=True)
def get_content_by_type(context, template_type, *args, **kwargs):
    app = context['request'].app
    language = context['request'].language

    limit = kwargs.get('limit', None)

    preview = context.get('preview', False)
    template_content_ids = TemplateContentTypes.objects.filter(template_content__app=app,
                                template_type=template_type, template_content__published_at__isnull=preview).order_by('position').values_list('template_content_id', flat=True)

    if limit is not None:
        template_content_ids = template_content_ids[:limit]

    template_content_ids = list(template_content_ids)
    # does not preserve order
    localized_tcs = LocalizedTemplateContent.objects.filter(template_content_id__in=template_content_ids, language=language)

    localized_tcs = list(localized_tcs)
    localized_tcs.sort(key=lambda localized_tc: template_content_ids.index(localized_tc.template_content.id))

    return localized_tcs

'''
    returns all pages of a given type
'''
@register.simple_tag
def get_template_content_locale(template_content, language):
    return LocalizedTemplateContent.objects.filter(template_content=template_content, language=language).first()

'''
    fetch content by template_name
'''
@register.simple_tag(takes_context=True)
def get_template_content(context, template_name, *args, **kwargs):
    app = context['app']
    
    language = context['request'].language
    limit = kwargs.get('limit', None)

    preview = context.get('preview', False)
    template_content_ids = TemplateContent.objects.filter(app=app, template_name=template_name).values_list(
        'id', flat=True)

    if limit is not None:
        template_content_ids = template_content_ids[:limit]

    template_content_ids = list(template_content_ids)
    
    # does not preserve order
    query_kwargs = {
        'template_content_id__in' : template_content_ids,
        'language' : language,
    }

    if preview == False:
        query_kwargs['published_at__isnull'] = False

    localized_tcs = LocalizedTemplateContent.objects.filter(**query_kwargs)
    localized_tcs = list(localized_tcs)
    
    localized_tcs.sort(key=lambda localized_tc: template_content_ids.index(localized_tc.template_content.id))

    return localized_tcs


'''
    common tag for microcontent(images and html)
'''
''' maybe deprecated
@register.simple_tag(takes_context=True)
def cms_getall(context, microcontent_category, microcontent_type, *args, **kwargs):

    template_content = context['template_content']
    preview_or_published = context.get('preview', 'published')

    Model = microcontent_category_model_map[microcontent_category][preview_or_published]
    microcontent = Model.objects.filter(template_content=template_content)

    dic = {}
    dic[microcontent_type] = microcontent
    
    return dic
'''

'''
    cms_get
    - fetch content from db / declare a user-defineable content
    - template_content_specific (template_content in context)
    - base.html (template_content not in context)    
'''
def cms_get(context, microcontent_category, microcontent_type, *args, **kwargs):

    template_content = context.get('template_content', None)
    preview = context.get('preview', False)
    language = context['request'].language
    localized_microcontent = None

    microcontent_model_type = 'draft' if preview else 'published'

    Model = microcontent_category_model_map[microcontent_category][microcontent_model_type]

    _microcontent = Model.objects.filter(Q(template_content=template_content, microcontent_type=microcontent_type) | Q(template_content__isnull=True, microcontent_type=microcontent_type)).first()
        
    if _microcontent:
        #if microcontent.template_content == None:
        #    preview = True
        localized_microcontent = _microcontent.get_content(language)

    return localized_microcontent


'''
    cms_get_multiple
    - fetch multiple contents of the same microcontent_category+microcontent_type from db
'''
@register.simple_tag(takes_context=True)
def cms_get_multiple(context, microcontent_category, microcontent_type, *args, **kwargs):

    template_content = context.get('template_content', None)
    preview = context.get('preview', False)
    language = context['request'].language

    microcontent_model_type = 'draft' if preview else 'published'

    Model = microcontent_category_model_map[microcontent_category][microcontent_model_type]
    _microcontents = Model.objects.filter(Q(template_content=template_content, microcontent_type=microcontent_type) | Q(template_content__isnull=True, microcontent_type=microcontent_type))

    microcontents = []
    for microcontent in _microcontents:
        localized_content = microcontent.get_content(language)
        
        if localized_content:
            microcontents.append(localized_content)
    
    return microcontents


'''
    shortcuts for getting MicroContent
'''
@register.simple_tag(takes_context=True)
def cms_get_microcontent(context, microcontent_type, *args, **kwargs):
    html = cms_get(context, 'microcontent', microcontent_type, *args, **kwargs)
    return html


@register.simple_tag(takes_context=True)
def cms_get_microcontents(context, microcontent_type, *args, **kwargs):
    html = cms_get_multiple(context, 'microcontents', microcontent_type, *args, **kwargs)
    return html


@register.simple_tag(takes_context=True)
def cms_get_image(context, microcontent_type, *args, **kwargs):
    image = cms_get(context, 'image', microcontent_type, *args, **kwargs)
    return image

'''
    multiple images
'''
@register.simple_tag(takes_context=True)
def cms_get_images(context, microcontent_type, *args, **kwargs):
    image = cms_get_multiple(context, 'image', microcontent_type, *args, **kwargs)
    return image


@register.filter
def template_content_translation_complete(template_content, language):
    ltc = template_content.get_localized(language)

    if not ltc:
        return False

    else:
        return ltc.translation_complete()


@register.simple_tag(takes_context=True)
def get_sections(context, *args, **kwargs):
    app = context['request'].app

    settings = app.get_theme_settings()

    sections = []
    
    for section, dic in settings['sections'].items():
        sections.append(section)
    return sections


@register.simple_tag
def get_localized_microcontent(instance, language):    
    return instance.get_content(language)

@register.simple_tag
def get_localized_attribute(template_content, language, attr):

    ltc = LocalizedTemplateContent.objects.filter(template_content=template_content, language=language).first()

    if ltc:
        return getattr(ltc, attr)

    return None

'''
    by default fetches latest db entry
    make this configurable
'''
@register.simple_tag(takes_context=True)
def include_latest_content(context, template_name):
    kwargs = {
        'limit' : 1,
    }
    localized_tcs = get_template_content(context, template_name, **kwargs)
    
    if localized_tcs:

        localized_template_content = localized_tcs[0]

        template = localized_template_content.get_template()

        template_context = Context({
            'preview' : kwargs.get('preview', False),
            'request': context['request'],
            'template_content': localized_template_content.template_content,
            'localized_template_content' : localized_template_content,
        })
        return template.render(template_context)

    return None


@register.simple_tag(takes_context=True)
def include_content(context, localized_template_content):
    
    template = localized_template_content.get_template()
    preview = context.get('preview', False)

    # create the correct context
    template_context = Context({
        'preview' : preview,
        'request': context['request'],
        'template_content': localized_template_content.template_content,
        'localized_template_content' : localized_template_content,
    })
    return template.render(template_context)


@register.simple_tag
def image_url(image):
    try:
        return image.url
    except:
        return ''
