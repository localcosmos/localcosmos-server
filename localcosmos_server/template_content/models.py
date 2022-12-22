from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template.defaultfilters import slugify
from django.core.files import File
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.models import App, ServerContentImageMixin, TaxonomicRestriction

from django.utils import timezone

import os, json, uuid

from.Templates import Template

PUBLISHED_IMAGE_TYPE_PREFIX = 'published-'

TEMPLATE_TYPES = (
    ('page', _('Page')), 
)

NAVIGATION_LINK_NAME_MAX_LENGTH = 30
TITLE_MAX_LENGTH = 255

def get_template_content_root(template_content):

    template_definition = template_content.draft_template.definition

    template_content_folder_name = '{0}-{1}'.format(template_definition['templateName'], template_content.pk)
    
    path = '/'.join(['localcosmos-server', 'template-content', 'published', template_content_folder_name])

    return path

# store published template here
def get_published_template_path(template_content, filename):
    template_content_root = get_template_content_root(template_content)
    unchanged_filename = os.path.basename(template_content.draft_template.template_filepath)
    path = '/'.join([template_content_root, 'template', filename])

    return path

def get_published_template_definition_path(template_content, filename):
    template_content_root = get_template_content_root(template_content)
    unchanged_filename = os.path.basename(template_content.draft_template.template_definition_filepath)
    path = '/'.join([template_content_root, 'template', unchanged_filename])

    return path

'''
    Templates and their definitions can rely in two different paths
'''
class TemplateContentManager(models.Manager):

    def create(self, creator, app, language, draft_title, draft_navigation_link_name, template_name,
               template_type):
        
        template_content = self.model(
            app = app,
            draft_template_name = template_name,
            template_type = template_type,
            tag = slugify(draft_title),
        )
        template_content.save()

        # create the localized template content
        localized_template_content = LocalizedTemplateContent.objects.create(creator, template_content, language,
                                            draft_title, draft_navigation_link_name)

        return template_content

    
    def filter_by_taxon(self, lazy_taxon, ascendants=False):

        template_contents = []

        if ascendants == False:

            template_content_content_type = ContentType.objects.get_for_model(TemplateContent)
            
            taxon_latname = lazy_taxon.taxon_latname
            taxon_author=lazy_taxon.taxon_author
            taxon_source = lazy_taxon.taxon_source

            template_content_links = TaxonomicRestriction.objects.filter(content_type=template_content_content_type,
                taxon_source=taxon_source, taxon_latname=taxon_latname, taxon_author=taxon_author)

            template_content_ids = template_content_links.values_list('object_id', flat=True)

            template_contents = self.filter(pk__in=template_content_ids)


        else:
            # get for all nuids, not implemented yet
            taxon_nuid = lazy_taxon.taxon_nuid

        
        return template_contents


'''
    TemplateContent
    - a "hybrid" component: during build, all template contens are built for offline use
    - template content which is not available offline can be fetched using the API
    - this can only work if some sort of menu is being fetched from the server
    - template content does not have to be part of a menu
    - offline (build) template content is never newer than the online version
    - the app can query online to get new contents, should also fetch template then

    published_template:
        The actual template and its definition are stored in the database rather then store a path 
        to the files. The user might upload a newer template version (as a file). This should not
        have any effect on the stored pages.

    draft_template:
        only the name is saved. the Template class looks up actual files. The draf always uses the template
        which is currently available as a file (with its definition as a file)
'''
class TemplateContent(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    app = models.ForeignKey(App, on_delete=models.CASCADE)

    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)

    # if a taxon is added to this content, it receives this tag during build
    tag = models.CharField(max_length=100, editable=False)

    draft_template_name = models.CharField(max_length=355) # stores the actual template (e.g. .html)

    published_template = models.FileField(null=True, upload_to=get_published_template_path)
    published_template_definition = models.FileField(null=True, upload_to=get_published_template_definition_path)

    objects = TemplateContentManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # use the templates on disk
        self.draft_template = Template(self.app, self.draft_template_name)

        if self.published_template:
            # the published template, use the template data (definition&template) stored in the db
            self.template = Template(self.app, self.name,
                self.published_template.path, self.published_template_definition.path)

    @property
    def name (self):
        return self.draft_template.definition['templateName']

    def get_locale(self, language_code):
        return LocalizedTemplateContent.objects.filter(template_content=self, language=language_code).first()

    def translation_complete(self, language_code):

        translation_errors = []

        ltc = LocalizedTemplateContent.objects.filter(template_content=self, language=language_code).first()

        if not ltc:
            translation_errors.append(_('Translation for the language %(language)s is missing') %{
                'language':language_code})

        else:
            #if ltc.language != self.app.primary_language and ltc.translation_ready == False:
            #    translation_errors.append(_('The translator for the language %(language)s is still working') %{
            #    'language':language_code})
                
            translation_errors += ltc.translation_complete()


        return translation_errors

    def publish(self, language='all'):
        
        publication_errors = []

        primary_language = self.app.primary_language
        secondary_languages = self.app.secondary_languages()
        
        if language == 'all':
            languages = self.app.languages()
        else:
            languages = [language]

        # translation_ready is currently not in use
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

            # store TemplateContent.published_template and TemplateContent.published_template_definition
            filepaths = [self.draft_template.template_filepath, self.draft_template.template_definition_filepath]

            for filepath in filepaths:

                with open(filepath, 'r') as template_file:
                    filename = os.path.basename(filepath)
                    djangofile = File(template_file)

                    if filepath == self.draft_template.template_filepath:
                        self.published_template.save(filename, djangofile)

                    if filepath == self.draft_template.template_definition_filepath:
                        self.published_template_definition.save(filename, djangofile)

        return publication_errors


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
        return self.name


MAX_SLUG_LENGTH = 100
class LocalizedTemplateContentManager(models.Manager):

    def create(self, creator, template_content, language, draft_title, draft_navigation_link_name):
        
        slug = self.generate_slug(draft_title)

        localized_template_content = self.model(
            created_by = creator,
            template_content = template_content,
            language = language,
            draft_title = draft_title,
            draft_navigation_link_name = draft_navigation_link_name,
            slug = slug,
        )
        
        localized_template_content.save()

        return localized_template_content


    def generate_slug_base(self, draft_title):
        slug_base = str('{0}'.format(slugify(draft_title)) )[:MAX_SLUG_LENGTH-1]

        return slug_base

    def generate_slug(self, draft_title):
        
        slug_base = self.generate_slug_base(draft_title)

        slug = slug_base

        exists = LocalizedTemplateContent.objects.filter(slug=slug).exists()

        i = 2
        while exists:
            
            if len(slug) > 50:
                slug_base = slug_base[:-1]
                
            slug = str('{0}-{1}'.format(slug_base, i))
            i += 1
            exists = LocalizedTemplateContent.objects.filter(slug=slug).exists()

        return slug


class LocalizedTemplateContent(ServerContentImageMixin, models.Model):

    language = models.CharField(max_length=15)

    template_content = models.ForeignKey(TemplateContent, on_delete=models.CASCADE)

    draft_title = models.CharField(max_length=TITLE_MAX_LENGTH)
    published_title = models.CharField(max_length=TITLE_MAX_LENGTH, null=True)

    draft_navigation_link_name = models.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH)
    published_navigation_link_name = models.CharField(max_length=NAVIGATION_LINK_NAME_MAX_LENGTH, null=True)

    slug = models.SlugField(unique=True)# localized slug

    draft_contents = models.JSONField(null=True)
    published_contents = models.JSONField(null=True)

    translation_ready = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                related_name='template_content_creator', null=True)
                                
    last_modified = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    draft_version = models.IntegerField(default=1)
    published_version = models.IntegerField(null=True)
    published_at = models.DateTimeField(null=True)

    objects = LocalizedTemplateContentManager()

    '''
    - if the language is the primary language, check if all required fields are present
    - if the language is a secondary language, check if all fields of the primary language are translated
    '''
    def translation_complete(self):

        translation_errors = []

        primary_language = self.template_content.app.primary_language

        template_definition = self.template_content.draft_template.definition
        contents = template_definition['contents']

        if self.language == primary_language:

            for content_key, content_definition in contents.items():

                if content_definition['type'] == 'text':

                    if 'required' in content_definition and content_definition['required'] == False:
                        continue

                    content = self.draft_contents.get(content_key, None)

                    if not content:
                        translation_errors.append(_('The component "%(component_name)s" is required but still missing for the language %(language)s.') %{'component_name':content_key, 'language':self.language})
        
        # secondary languages: check if all fields that are present in the primary language have been translated
        else:
            primary_locale = self.template_content.get_locale(primary_language)

            primary_contents = primary_locale.draft_contents

            if not primary_contents:
                translation_errors.append(_('Content is still missing for the language %(language)s.') % {'language':primary_language})

            else:
                for content_key, content in primary_contents.items():
                    if content_key not in self.draft_contents or not self.draft_contents[content_key]:
                        translation_errors.append(_('The translation for the language %(language)s is incomplete.') % {'language':self.language})
                        break

        return translation_errors


    @property
    def translation_is_complete(self):
        translation_errors = self.translation_complete()
        if translation_errors:
            return False
        return True


    def publish_images(self):

        template_definition = self.template_content.draft_template.definition
        contents = template_definition['contents']

        for content_key, content_definition in contents.items():

            content_images = []

            if content_definition['type'] == 'image':

                content_images = [self.image(image_type=content_key)]

            elif content_definition['type'] == 'multi-image':

                content_images = self.images(image_type=content_key)

            
            published_image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, content_key)

            old_published_images = self.images(image_type=published_image_type)
            old_published_images.delete()

            for content_image in content_images:
                published_content_image = content_image
                published_content_image.pk = None
                published_content_image.image_type = published_image_type
                published_content_image.save()


    def publish(self):
        # set title
        self.published_title = self.draft_title
        self.published_navigation_link_name = self.draft_navigation_link_name
        self.published_contents = self.draft_contents

        # currently, images are not translatable. This can change in the future
        if self.language == self.template_content.app.primary_language:
            self.publish_images()

        if self.published_version != self.draft_version:

            self.published_version = self.draft_version
            self.published_at = timezone.now()

        self.save(published=True)


    def save(self, *args, **kwargs):

        # indicates, if the save() command came from self.publish
        published = kwargs.pop('published', False)

        if not self.pk:

            if self.language != self.template_content.app.primary_language:
                master_ltc = self.template_content.get_locale(self.template_content.app.primary_language)
                self.draft_version = master_ltc.draft_version

        else:

            if published == False:

                # the localized_template_content has already been published. start new version
                if self.published_version == self.draft_version:
                    self.draft_version += 1
                    self.translation_ready = False

        super().save(*args, **kwargs)


    class Meta:
        unique_together=('template_content', 'language')


'''
class Navigation(models.Model):

    app = models.ForeignKey(App, on_delete=models.CASCADE)
    name = models.CharField(max_length=355)


class NavigationEntry(models.Model):

    navigation = models.ForeignKey(Navigation, on_delete=models.CASCADE)
    template_content = models.ForeignKey(TemplateContent, on_delete=models.CASCADE)
    parent_entry = models.ForeignKey('self', on_delete=models.CASCADE)
'''