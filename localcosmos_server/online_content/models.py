from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import slugify
from django import forms
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.core.files import File

from django.contrib.contenttypes.fields import GenericRelation
from content_licencing.models import ContentLicenceRegistry

from localcosmos_server.models import App

import os, json, secrets

from django.utils import timezone

from .fields import MultiContentField
from .widgets import MultiContentWidget


'''
    TEMPLATE CONTENT AND LOCALIZED TEMPLATE CONTENT

    template contents are .html templates with titles
    the templates contain MicroContents which are stored separately

    you cannot share single websites (TemplateContent) between apps
    therefore, template contents are tied to OnlineContent

    OnlineContent cannot be shared between apps, too
    
    There are two types of TemplateContent:
    - page
    - feature (can be displayed on several pages via include, may not extend a base)
'''

TEMPLATE_TYPES = (
    ('page', _('Page')), # pages can have flags like "header", "footer" etc
    ('feature', _('Feature')), # e.g. newsbox - can be displayed on several pages
)

class TemplateContentManager(models.Manager):

    def create(self, creator, app, language, draft_title, draft_navigation_link_name, template_name,
               template_type):
        
        template_content = self.model(
            app = app,
            template_name = template_name,
            template_type = template_type,
        )
        template_content.save()

        # create the localized template content
        localized_template_content = LocalizedTemplateContent.objects.create(creator, template_content, language,
                                            draft_title, draft_navigation_link_name)

        return template_content


class TemplateContent(models.Model):

    app = models.ForeignKey(App, on_delete=models.CASCADE)
    template_name = models.CharField(max_length=255) # the .html django template this content uses
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES) # page or feature

    objects = TemplateContentManager()

    def get_theme_settings(self):
        return self.app.get_online_content_settings()

    def verbose_template_name(self, language_code=None):
        if not language_code:
            language_code = self.app.primary_language
            
        theme_settings = self.app.get_online_content_settings()

        verbose_name = self.template_name

        if self.template_name in theme_settings['verbose_template_names'] and language_code in theme_settings['verbose_template_names'][self.template_name]:
            verbose_name = theme_settings['verbose_template_names'][self.template_name][language_code]

        return verbose_name
        

    def get_localized(self, language_code):

        localized_template_content = LocalizedTemplateContent.objects.filter(template_content=self,
                                                                             language=language_code).first()
        return localized_template_content

    def locales(self):
        return LocalizedTemplateContent.objects.filter(template_content=self)

    # template_path dependant of the apps theme setting
    def template_path(self, app):
        return os.path.join(self.app.get_online_content_templates_path(), self.template_name)

    
    def get_template(self):
        return self.app.get_online_content_template(self.template_name)
    

    def primary_title(self):
        language_code = self.app.primary_language
        locale = LocalizedTemplateContent.objects.filter(template_content=self, language=language_code).first()

        if locale:
            return locale.draft_title
        else:
            return None


    # might be obsolete
    def validate(self, app):

        result = {
            'errors' : [],
            'warnings' : [],
        }

        return result


    '''
    TemplateContent.translation_complete(language_code)
    - checks if all localized_template_contents are set to translation_ready
    - calls LocalizedTemplateContent.translation_complete()
    ---- if language is the primary language: check if all required fields are present
    ---- if language is a secondary language: check if all fields of the primary language are translated
    '''
    def translation_complete(self, language_code):

        translation_errors = []
        
        ltc = LocalizedTemplateContent.objects.filter(template_content=self, language=language_code).first()

        if not ltc:
            translation_errors.append(_('Translation for the language %(language)s is missing') %{
                'language':language_code})

        else:
            if ltc.translation_ready == False:
                translation_errors.append(_('The translator for the language %(language)s is still working') %{
                'language':language_code})
                
            translation_errors += ltc.translation_complete()
            
        return translation_errors


    def publish(self, language='all'):

        publication_errors = []

        secondary_languages = self.app.secondary_languages()
        primary_language = self.app.primary_language


        if language == 'all':
            languages = self.app.languages()
        else:
            languages = [language]

        # ltc.translation_ready is not set to True by the user if there is only one language
        # skip the check if the "translation" exists and also skip the check if the user has set
        # translation_ready to True, which is not the case because there is only a "publish" button
        # in this case (only 1 language) and no "ready for translation" button
        if not secondary_languages:
            ltc = LocalizedTemplateContent.objects.filter(template_content=self, language=primary_language).first()
            publication_errors += ltc.translation_complete()

        # secondary languages exist. these languages need translators and the translation_ready flags are
        # set by the user when he has finished translating
        else:

            for language_code in languages:

                # translation_complete checks two things:
                # a) if the primary language has filled all required fields
                # b) if all secondary languages are translated completely
                publication_errors += self.translation_complete(language_code)

        # below this, no error checks are allowed because published_versions are being set

        if not publication_errors:

            for language_code in languages:
            
                ltc = LocalizedTemplateContent.objects.filter(template_content=self, language=language_code).first()
                if ltc:
                    ltc.publish()

            # get all lang independant DraftTextMicroContent and DraftImageMicroContent instances
            # and publish all LocalizedDraft*MicroContent for the given language(s)
            # this cannot be done from the LocalizedTemplateContent as different languages link to
            # the same Published*MicroContent

            # ROUTINE: first, publish the Draft*Microcontent, this creates Published*MicroContent
            # then publish all LocalizedPublished*MicroContents and attach them to the already
            # created Published*MicroContent


            # get all subclasses of PublishedCMSMicrocontent, eg PublishedTextMicroContent or PublishedImageMicroContent
            PublishedMetaClasses = PublishedCMSMicroContent.__subclasses__()

            for PublishedMetaClass in PublishedMetaClasses:
                published_microcontents = PublishedMetaClass.objects.filter(template_content=self)

                for published_microcontent in published_microcontents:
                    published_microcontent.delete()


            # get all sublasses of DraftCMSMicroContent:
            DraftMetaClasses = DraftCMSMicroContent.__subclasses__()
            
            for DraftMetaClass in DraftMetaClasses:
                
                draft_microcontents = DraftMetaClass.objects.filter(template_content=self)

                for draft_microcontent in draft_microcontents:
                    draft_microcontent.publish(languages)            

        return publication_errors
    

    def flags(self):
        return list(TemplateContentFlags.objects.filter(template_content=self).values_list('flag', flat=True))

    def unpublish(self):
        localizations = LocalizedTemplateContent.objects.filter(template_content=self)

        for localization in localizations:
            localization.published_version = None
            localization.published_at = None
            localization.save()
        

    @property
    def is_published(self):
        return LocalizedTemplateContent.objects.filter(template_content=self,
                                                       published_version__isnull=False).exists()

        
    def __str__(self):
        ltc = self.get_localized(self.app.primary_language)

        if ltc:
            return ltc.draft_title

        return 'Template Content %s' %self.pk
    

'''
    on db entry per language and content -> LocalizedTemplateContent
    slugs are also localized
'''
MAX_SLUG_LENGTH = 100
class LocalizedTemplateContentManager(models.Manager):

    def create(self, creator, template_content, language, draft_title, draft_navigation_link_name):
        
        slug = self.generate_slug(draft_title)

        localized_template_content = self.model(
            creator = creator,
            template_content = template_content,
            language = language,
            draft_title = draft_title,
            draft_navigation_link_name = draft_navigation_link_name,
            slug = slug,
        )
        
        localized_template_content.save()

        return localized_template_content


    def generate_slug_base(self, draft_title):
        slug_base = str('%s' % (slugify(draft_title)) )[:MAX_SLUG_LENGTH-1]

        return slug_base

    def generate_slug(self, draft_title):
        
        slug_base = self.generate_slug_base(draft_title)

        slug = slug_base

        exists = LocalizedTemplateContent.objects.filter(slug=slug).exists()

        i = 2
        while exists:
            
            if len(slug) > 50:
                slug_base = slug_base[:-1]
                
            slug = str('%s-%s' % (slug_base, i))
            i += 1
            exists = LocalizedTemplateContent.objects.filter(slug=slug).exists()

        return slug


'''
    translation_ready is set by the translator to signal that he has finished the translation
'''
# the maximum character count for a link name
NAVIGATION_LINK_NAME_MAX_LENGTH = 30
TITLE_MAX_LENGTH = 255

class LocalizedTemplateContent(models.Model):
    template_content = models.ForeignKey(TemplateContent, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)# localized slug
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)

    # title
    # the title is needed e.g. for displaying a name of the content in the admin
    draft_title = models.CharField(max_length=TITLE_MAX_LENGTH)
    published_title = models.CharField(max_length=TITLE_MAX_LENGTH, null=True)

    # link name in navigations
    # link names in navs have to be short. In-Text links can have different names an are set by the editor on demand
    draft_navigation_link_name = models.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH)
    navigation_link_name = models.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                related_name='template_content_creator', null=True)
    last_modified = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    draft_version = models.IntegerField(default=1)
    published_version = models.IntegerField(null=True)
    published_at = models.DateTimeField(null=True)
    
    translation_ready = models.BooleanField(default=False)

    # for protecting previews
    preview_token = models.CharField(max_length=255, null=True)
    preview_token_created_at = models.DateTimeField(null=True)

    objects = LocalizedTemplateContentManager()        


    '''
    - if the language is the primary language, check if all required fields are presend
    - if the language is a secondart language, check if all fields of the primary language are translated
    '''
    def translation_complete(self):

        translation_errors = []

        primary_language = self.template_content.app.primary_language

        # avoid circular import
        from .parser import TemplateParser
        parser = TemplateParser(self.template_content.app, self.template_content, self.get_template())

        cms_tags = parser.parse()

        # primary language: check if all required fields are present
        if self.language == primary_language:
            # in this case, the page editor has pushed "translation_complete" button or "publish" button
            # on the creation page, no the translation page
            # check if all required components are presend
            # load the parser
            
            for tag in cms_tags:
                if not 'optional' in tag.args:
                    
                    draft_microcontent = tag.Model.objects.filter(template_content=self.template_content,
                                                                  microcontent_type=tag.microcontent_type).first()

                    if not draft_microcontent:
                        translation_errors.append(_('The component "%(component_name)s" is required but still missing for the language %(language)s') %{'component_name':tag.microcontent_type, 'language':self.language})

                    else:
                        translation_errors += draft_microcontent.translation_complete(self.language)

        # secondary languages: check if all fields that are present in the primary language have been translated           
        else:
            for tag in cms_tags:

                # language independant - fetch all existing drafts
                draft_microcontents = tag.Model.objects.filter(template_content=self.template_content,
                                                               microcontent_type=tag.microcontent_type)

                # check all contents, including all 'multi' 
                for draft_microcontent in draft_microcontents:

                    translation_errors += draft_microcontent.translation_complete(self.language)

        return translation_errors
    

    def flags(self):
        return self.template_content.flags()

    # preview token
    def update_preview_token(self):
        self.preview_token = secrets.token_hex(20)
        self.preview_token_created_at = timezone.now()
        self.save(disallow_new_version=True)

    def validate_preview_token(self, token, maxage_minutes=240):
        
        if self.preview_token and self.preview_token_created_at:

            if self.preview_token != token:
                return False

            now = timezone.now()
            timedelta = (now - self.preview_token_created_at).total_seconds() / 60
            # create new token every 5 minutes
            # each token is valid for 60 minutes
            if timedelta > maxage_minutes:
                return False

            return True

        return False

    # shortcut
    def get_template(self):
        return self.template_content.get_template()

    # improvement could be: read urls.js from the app and construct the url accordingly
    def in_app_link(self, app_state='published'):
        if app_state == 'preview':
            in_app_link = '/online-content/%s/%s/' %(self.slug, self.preview_token)
        else:
            in_app_link = '/online-content/%s/' %(self.slug)

        return in_app_link


    '''
    publish a LocalizedTemplateContent and all its MicroContents
    '''
    def publish(self):
        # set title
        self.published_title = self.draft_title
        self.navigation_link_name = self.draft_navigation_link_name

        if self.published_version != self.draft_version:

            self.published_version = self.draft_version
            self.published_at = timezone.now()

        self.save(published=True)
        

    def save(self, *args, **kwargs):

        # indicates, if the save() command came from self.publish
        published = kwargs.pop('published', False)
        
        # if only a new preview token is needed skip the publication protocol
        disallow_new_version = kwargs.pop('disallow_new_version', False)

        # first, check the slug - new slug if the title really changed
        slug_base = LocalizedTemplateContent.objects.generate_slug_base(self.draft_title)
        if not self.slug.startswith(slug_base):
            old_slug = self.slug
            self.slug = LocalizedTemplateContent.objects.generate_slug(self.draft_title)
            new_slug = self.slug

            # add to SlugTrail - make old links still work
            slug_trail = SlugTrail(
                old_slug = old_slug,
                new_slug = new_slug,
            )

            slug_trail.save()

        if not self.pk:

            if self.language != self.template_content.app.primary_language:
                master_ltc = self.template_content.get_localized(self.template_content.app.primary_language)
                self.draft_version = master_ltc.draft_version

        else:

            if disallow_new_version == False and published == False:

                # the localized_template_content has already been published. start new version
                if self.published_version == self.draft_version:
                    self.draft_version += 1
                    self.translation_ready = False

        super().save(*args, **kwargs)


# if a slug is changed, remember the wold slug for a forward
# e.g. a user changes the title of an entry
class SlugTrail(models.Model):
    old_slug = models.SlugField()
    new_slug = models.SlugField()

    class Meta:
        unique_together = ('old_slug', 'new_slug')


'''
    TemplateContentFlags Concept
    - assign flags to template_content, like 'footer' or 'header' or 'nav'
    - multiple assignments possible - one template_content can have multiple flags
      and occur e.g. in header and also in footer
    - nested/multi-level flagging is possible
    - there should not be so many db entries, so a simple parent_flag model should be fast enough
'''

'''
    The FlagTree class enables iterating over a tree structure
    {
        "name" : "text",
        "children" : {
            "name" : "text"
        }
    }

    max_levels is 2 by default
'''
class FlagTree:

    # flags is a TemplateContentFlags QuerySet
    def __init__(self, flags, language, max_levels=2, **kwargs):
        self.flags = flags.order_by('parent_flag')
        self.language = language
        self.flag_tree = {}
        
        self.app_state = kwargs.get('app_state', 'published')

        self.toplevel_count = 0

        # preview fetches localized_template_content.draft_title
        title_attr = 'published_title'
        navigation_link_attr = 'navigation_link_name'
        if self.app_state == 'preview':
            title_attr = 'draft_title'
            navigation_link_attr = 'draft_navigation_link_name'

        
        for flag in self.flags:

            tree_entry = self.get_tree_entry(flag)

            if tree_entry is not None:

                self.toplevel_count += 1

                if flag.parent_flag:
                    raise NotImplementedError('navigation nesting is not implemented yet')

                localized_template_content = tree_entry['localized_template_content'] 

                self.flag_tree[getattr(localized_template_content, title_attr)] = tree_entry


    def get_tree_entry(self, flag):

        tree_entry = None

        # only return unpublished localized_template_contents if preview is set to True
        localized_template_content = flag.template_content.get_localized(self.language)

        if localized_template_content:
            if self.app_state == 'preview' or localized_template_content.published_version:

                tree_entry = {
                    'localized_template_content' : localized_template_content,
                    'children' :[],
                    'in_app_link' : localized_template_content.in_app_link(app_state=self.app_state),
                    'navigation_link_name' : localized_template_content.navigation_link_name,
                }

                if self.app_state == 'preview':
                    tree_entry['navigation_link_name'] = localized_template_content.draft_navigation_link_name

        return tree_entry
        

    def __iter__(self):
        for draft_title, tree_entry in self.flag_tree.items():
            yield tree_entry

    def __bool__(self):
        if self.flag_tree.items():
            return True
        return False
            

class TemplateContentFlagsManager(models.Manager):

    # do not retrieve flags across apps
    def get_tree(self, app, flag, language, **kwargs):

        theme_settings = app.get_online_content_settings()
        max_flag_levels = theme_settings.get('max_flag_levels', 2)

        flags = self.filter(template_content__app=app, flag=flag)

        flag_tree = FlagTree(flags, language, max_levels=max_flag_levels, **kwargs)

        return flag_tree
    
    
class TemplateContentFlags(models.Model):
    template_content = models.ForeignKey(TemplateContent, on_delete=models.CASCADE)
    flag = models.CharField(max_length=255) # e.g. 'footer', 'nav', 'header'
    parent_flag = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    position = models.IntegerField(default=1)

    objects = TemplateContentFlagsManager()

    class Meta:
        unique_together = ('template_content', 'flag')


'''
    MICROCONTENT
    - linked to a template_content (there can be multiple template_contents of the same type)
    - 1:n relation (TemplateContent : MicroContent)
    - separates layout from text/images

    TYPES (microcontent_type) are defined by the template creator 
'''
class CMSMicroContentManager(models.Manager):

    # return LocalizedCMSMicroContent instances in pk order
    def get_language_dependant(self, template_content, microcontent_type, language):

        contents = []

        # filter the unlocalized model
        contents_ = self.filter(template_content=template_content, microcontent_type=microcontent_type).order_by(
            'pk', 'position')

        for content in contents_:
            LocaleModel = self.model.get_locale_model()
            lmcs = LocaleModel.objects.filter(microcontent=content, language=language)

            for lmc in lmcs:
                contents.append(lmc)

        return contents


class DraftMicroContentManager(CMSMicroContentManager):

    def create(self, template_content, language, microcontent_type, content, creator, **kwargs):

        draft_microcontent = self.model(
            template_content = template_content,
            microcontent_type = microcontent_type,
        )

        draft_microcontent.save()

        LocaleModel = self.model.get_locale_model()

        localized_draft_microcontent = LocaleModel.objects.create(draft_microcontent, language, content, creator)

        return draft_microcontent


from django.db.models.fields.files import FileField
from django.core.files import File
from django.core.files.base import ContentFile
class PublishedMicroContentManager(CMSMicroContentManager):

    def create(self, draft_microcontent, **kwargs):


        # first publish the not-localized microcontent
        microcontent_fields = self.model._meta.get_fields(include_parents=False)
        pmc_fields = {}

        for mc_field in microcontent_fields:
            
            if mc_field.concrete == False:
                continue
            
            # field.primary_key = bool indicated if the field is the primary key
            if mc_field.primary_key:
                continue
            pmc_fields[mc_field.name] = getattr(draft_microcontent, mc_field.name)

        published_microcontent = self.model(**pmc_fields)
        published_microcontent.save()

        return published_microcontent


'''
    Abstract CMSMicroContent
'''
class CMSMicroContent(models.Model):
    template_content = models.ForeignKey(TemplateContent, on_delete=models.CASCADE, null=True) # if template_content is None, it is the same content for every template_content
    microcontent_type = models.CharField(max_length=255)
    position = models.IntegerField(default=1)

    @classmethod
    def get_locale_model(self):
        return globals()['Localized%s' % self._meta.model.__name__]


    def get_content(self, language):
        lmc = self.get_localized(language)

        if lmc:
            return lmc.get_content()
        
        return None


    def get_localized(self, language):

        LocaleModel = self.get_locale_model()        
        lmc = LocaleModel.objects.filter(microcontent=self, language=language).first()
        
        return lmc
    
  
    class Meta:
        ordering = ['pk', 'position']
        abstract = True



'''
    Draft and Published Microcontents require some methods and separate Managers
'''
class DraftCMSMicroContent(CMSMicroContent):

    objects = DraftMicroContentManager()

    @classmethod
    def get_publication_model(self):
        return globals()[self._meta.model.__name__.replace('Draft', 'Published')]

    def get_form_field(self, app, template_content, widget_attrs, *args, **kwargs):
        raise NotImplementedError('CMSMicroContent need a get_form_field method')

    def translation_complete(self, language):
        raise NotImplementedError('CMSMicroContent need a translation_complete method')

    def set_content(self, content, editor, language):
        lmc = self.get_localized(language)
        if not lmc:
            LocaleModel = self.get_locale_model()
            lmc = LocaleModel.objects.create(self, language, content, editor)
        else:
            lmc.content = content
            lmc.last_modified_by = editor
            lmc.save()


    '''
    the licences get published too, for images
    '''
    def publish(self, languages):

        PublicationModel = self.get_publication_model()

        # create the published microcontent, language independant
        published_microcontent = PublicationModel.objects.create(self)

        PublicationLocaleModel = published_microcontent.get_locale_model()

        # get the fields
        localized_published_microcontent_fields = PublicationLocaleModel._meta.get_fields(include_parents=False)

        # iterate over all languages that should be published and attach the localization to published_microcontent
        for language in languages:
            localized_draft_microcontent = self.get_localized(language)
            
            if localized_draft_microcontent:

                lpmc_fields = {
                    'microcontent' : published_microcontent,
                }
                file_field_names = []

                for lmc_field in localized_published_microcontent_fields:

                    if lmc_field.concrete == False:
                        continue

                    if lmc_field.primary_key or lmc_field.name == 'microcontent':
                        continue

                    if isinstance(lmc_field, FileField):
                        file_field_names.append(lmc_field.name)

                    lpmc_fields[lmc_field.name] = getattr(localized_draft_microcontent, lmc_field.name)


                # model instance without files
                localized_published_microcontent = PublicationLocaleModel(**lpmc_fields)

                # work the FileField/Imagefield etc fields
                # copy the file
                for file_field_name in file_field_names:

                    draft_file = getattr(localized_draft_microcontent, file_field_name)
               
                    new_file = ContentFile(draft_file.read())
                    new_file.name = os.path.split(draft_file.name)[-1]

                    setattr(localized_published_microcontent, file_field_name, new_file)
                    
                    draft_file.close()

                localized_published_microcontent.save()

                # generate the licences
                if hasattr(localized_draft_microcontent, 'licences'):
                    for licence in localized_draft_microcontent.licences.all():

                        content_licence = licence.content_licence()
                        licence_kwargs = {
                            'creator_name' : licence.creator_name,
                            'creator_link' : licence.creator_link,
                            'source_link' : licence.source_link,
                            'language' : licence.language,
                            'sha256' : licence.sha256,
                        }
                            
                        registry_entry = ContentLicenceRegistry.objects.register(localized_published_microcontent,
                            licence.model_field, licence.uploader, content_licence.short_name,
                            content_licence.version, **licence_kwargs)


    class Meta:
        abstract = True


class PublishedCMSMicroContent(CMSMicroContent):
    objects = PublishedMicroContentManager()

    class Meta:
        abstract = True


'''
    Abstract LocalizedCMSMicroContent
    - serves both Draft and Published
'''
class LocalizedCMSMicroContentManager(models.Manager):
    
    def create(self, microcontent, language, content, creator, **kwargs):

        # can be localized_draft_microcontent or localized_published_microcontent

        localized_microcontent = self.model(
            language = language,
            microcontent = microcontent,
            content = content,
            creator = creator,
            **kwargs
        )

        localized_microcontent.save()

        return localized_microcontent


class LocalizedCMSMicroContent(models.Model):
    
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+',
                                         null=True)
    last_modified = models.DateTimeField(auto_now=True)

    objects = LocalizedCMSMicroContentManager()


    def get_content(self):
        if type(self.content) == str:
            return mark_safe(self.content)
        return self.content

    class Meta:
        abstract = True
        unique_together = ('microcontent', 'language')


'''
    MicroContent
    - are parts of template_contents that the user can fill with text
    - is restricted to one template_content
    - can have one or more images linked to it
    - can be layoutable or not
'''


################################ TEXT MICROCONTENT ######################################
'''
    Draft Text MicroContent
    - can be deleted and edited
    - deleting these elements does not affect the published content
'''
class DraftTextMicroContent(DraftCMSMicroContent):

    def get_form_field(self, app, template_content, widget_attrs, *args, **kwargs):

        widget = forms.Textarea
        if 'short' in args:
            widget = forms.TextInput
            

        if 'multi' in widget_attrs:
            # assign the number
            widget_attrs['widget'] = widget
            return MultiContentField(widget=MultiContentWidget(widget_attrs), **kwargs)

        else:
            kwargs['widget'] = widget
            return forms.CharField(**kwargs)


    def translation_complete(self, language):

        translation_errors = []
        
        lmc = self.get_localized(language)

        if not lmc or (lmc.content is None or len(lmc.content) == 0):
            translation_errors.append(_('%(component_name)s is missing for the language %(language)s' %{'component_name':self.microcontent_type, 'language':language}))

        return translation_errors


'''
    Published Text MicroContent
    - cannot be edited
    - is not affected by deletions in the draft
    - is not affected if a whole DraftCMSMicroConent instance is deleted
'''

class PublishedTextMicroContent(PublishedCMSMicroContent):
    pass


'''
    Localizations for Text MicroContents
    content = html
    plain_text = text only
    on each save, the plain text is updated
'''
class LocalizedTextMicroContent(LocalizedCMSMicroContent):
    
    content = models.TextField(null=True)
    plain_text = models.TextField(null=True)

    def save(self, *args, **kwargs):
        
        if self.content is not None:
            self.plain_text = _generate_plaintext(self.content)
        else:
            self.plain_text = None
             
        return super().save(*args, **kwargs)
    

    class Meta:
        abstract = True


'''
    localized draft TextMicroContent
'''
class LocalizedDraftTextMicroContent(LocalizedTextMicroContent):
    microcontent = models.ForeignKey(DraftTextMicroContent, on_delete=models.CASCADE)


'''
    localized published TextMicroContent
'''
class LocalizedPublishedTextMicroContent(LocalizedTextMicroContent):
    microcontent = models.ForeignKey(PublishedTextMicroContent, on_delete=models.CASCADE)


################################ IMAGE MICROCONTENT ######################################

'''
    ImageMicroContent
    - invoked by {% cms_get_image %}
    - microcontent_category = 'image'
'''

class DraftImageMicroContent(DraftCMSMicroContent):

    def get_form_field(self, app, template_content, widget_attrs, *args, **kwargs):

        language = widget_attrs['language']

        limc = self.get_localized(language)
        if limc:
            widget_attrs['file'] = limc.content


        data_url_kwargs = {
            'app_uid' : app.uid,
            'template_content_id' : template_content.id,
            'language' : language,
            'microcontent_category' : widget_attrs['data-microcontentcategory'],
        }

        licenced_url_kwargs = data_url_kwargs.copy()

        data_url_kwargs['microcontent_type'] = widget_attrs['data-microcontenttype']

        delete_url = None

        if self.pk:

            licenced_url_kwargs['microcontent_id'] = self.pk
            licenced_url = reverse('update_licenced_image', kwargs=licenced_url_kwargs)
            
            delete_kwargs = {
                'app_uid' : app.uid,
                'template_content_id' : template_content.id,
                'language' : language,
            }
            delete_url = reverse('DeleteFileContent', kwargs=delete_kwargs)
            
        else:
            licenced_url_kwargs['microcontent_type'] = widget_attrs['data-microcontenttype']
            licenced_url = reverse('upload_licenced_image', kwargs=licenced_url_kwargs)
            
        data_url = reverse('upload_image', kwargs=data_url_kwargs)
            
        widget_attrs['data-url'] = data_url  
        widget_attrs['accept'] = 'image/*'

        form_field = forms.ImageField(widget=forms.FileInput(widget_attrs), **kwargs)
        form_field.licenced_url = licenced_url
        form_field.delete_url = delete_url
        return form_field

    # always falls back to primary language image
    def translation_complete(self, language):
        return []

    # override set_content oft DraftCMSMicroContent for enabling the deletion of old image file
    def set_content(self, content, editor, language):

        limc = self.get_localized(language)

        if not limc:
            limc = LocalizedDraftImageMicroContent.objects.create(self, language, content, editor)
        else:
        
            limc.last_modified_by = editor
            old_filepath = limc.content.path
            
            limc.content = content
            limc.save()

            # delete old image file
            if old_filepath != limc.content.path:
                if os.path.isfile(old_filepath):
                    os.remove(old_filepath)


'''
    Published Image MicroContent
    - cannot be edited
    - is not affected by deletions in the draft
    - is not affected if a whole DraftCMSMicroConent instance is deleted
'''
class PublishedImageMicroContent(PublishedCMSMicroContent):

    licences = GenericRelation(ContentLicenceRegistry)


'''
    Localizations for ImageMicroContent
    content = ImageField
'''

'''
    paths where images (ImageMicroContents) are uploaded to
'''
def content_images_upload_path(instance, filename):

    # published or draft
    if isinstance(instance, LocalizedPublishedImageMicroContent):
        draft_or_published = 'published'
    else:
        draft_or_published = 'draft'

    if hasattr(instance.microcontent, 'template_content') and instance.microcontent.template_content is not None:
        subfolder = str(instance.microcontent.template_content.app.pk)
    else:
        subfolder = 'global'

    path = os.path.join('online_content', subfolder, 'content_images', draft_or_published,
                        instance.microcontent.microcontent_type, instance.language, filename)

    return path


class LocalizedImageMicroContent(LocalizedCMSMicroContent):

    content = models.ImageField(upload_to=content_images_upload_path)

    class Meta:
        abstract = True


class LocalizedDraftImageMicroContent(LocalizedImageMicroContent):
    microcontent = models.ForeignKey(DraftImageMicroContent, on_delete=models.CASCADE)

    licences = GenericRelation(ContentLicenceRegistry)


class LocalizedPublishedImageMicroContent(LocalizedImageMicroContent):
    microcontent = models.ForeignKey(PublishedImageMicroContent, on_delete=models.CASCADE)

    licences = GenericRelation(ContentLicenceRegistry)


'''
    Helpers
'''
def _generate_plaintext(text):
    text = strip_tags(text)
    return ' '.join(text.split())


microcontent_category_model_map = {
    'template_content' : {
        'draft' : TemplateContent,
        'published' : TemplateContent,
    },
    'template_contents' : {
        'draft' : TemplateContent,
        'published' : TemplateContent,
    },
    'microcontent' : {
        'draft' : DraftTextMicroContent,
        'published' : PublishedTextMicroContent,
    },
    'microcontents' : {
        'draft' : DraftTextMicroContent,
        'published' : PublishedTextMicroContent,
    },
    'image' : {
        'draft' : DraftImageMicroContent,
        'published' : PublishedImageMicroContent,
    },
    'images' : {
        'draft' : DraftImageMicroContent,
        'published' : PublishedImageMicroContent,
    },
}
