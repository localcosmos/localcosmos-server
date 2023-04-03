from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template.defaultfilters import slugify
from django.core.files import File

from localcosmos_server.models import App, ServerContentImageMixin, TaxonomicRestriction

from django.utils import timezone

import os, json, uuid, shutil

from.Templates import Template

from .utils import (get_component_image_type, get_published_image_type, PUBLISHED_IMAGE_TYPE_PREFIX,
                    get_frontend_specific_url)

TEMPLATE_TYPES = (
    ('page', _('Page')),
    ('component', _('Component')),
)

NAVIGATION_LINK_NAME_MAX_LENGTH = 20
TITLE_MAX_LENGTH = 255

def get_published_template_content_root(template_content):

    template_definition = template_content.draft_template.definition

    template_content_folder_name = '{0}-{1}'.format(template_definition['templateName'], template_content.pk)
    
    path = '/'.join(['localcosmos-server', 'template-content', 'published', template_content_folder_name])

    return path

# store published template here
def get_published_page_template_path(template_content, filename):
    template_content_root = get_published_template_content_root(template_content)
    unchanged_filename = os.path.basename(template_content.draft_template.template_filepath)
    path = '/'.join([template_content_root, 'templates', 'page', unchanged_filename])

    return path

def get_published_page_template_definition_path(template_content, filename):
    template_content_root = get_published_template_content_root(template_content)
    unchanged_filename = os.path.basename(template_content.draft_template.template_definition_filepath)
    path = '/'.join([template_content_root, 'templates', 'page', unchanged_filename])

    return path


# this is not used for django files, but for direct file operations. Include settings.MEDIA_ROOT
def get_published_component_templates_root(template_content):
    published_template_content_root = get_published_template_content_root(template_content)
    published_component_templates_root = os.path.join(settings.MEDIA_ROOT, published_template_content_root, 'templates', 'component')
    return published_component_templates_root


class PublicationMixin:

    def translation_complete(self, language_code):

        translation_errors = []

        localized_instance = self.get_locale(language_code)

        if not localized_instance:
            translation_errors.append(_('Translation for the language %(language)s is missing') %{
                'language':language_code})

        else:
            #if ltc.language != self.app.primary_language and ltc.translation_ready == False:
            #    translation_errors.append(_('The translator for the language %(language)s is still working') %{
            #    'language':language_code})
                
            translation_errors += localized_instance.translation_complete()


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
            localized_instance = self.get_locale(primary_language)
            publication_errors += localized_instance.translation_complete()

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
            
                localized_instance = self.get_locale(language_code)
                if localized_instance:
                    localized_instance.publish()
            
            self.publish_assets()

        return publication_errors

'''
    Templates and their definitions can rely in two different paths
'''
class TemplateContentManager(models.Manager):

    def create(self, creator, app, language, draft_title, template_name,
               template_type, assignment=None):
        
        template_content = self.model(
            app = app,
            draft_template_name = template_name,
            template_type = template_type,
            assignment=assignment,
        )
        template_content.save()

        # create the localized template content
        localized_template_content = LocalizedTemplateContent.objects.create(creator, template_content, language,
                                            draft_title)

        return template_content

    
    def filter_by_taxon(self, lazy_taxon, ascendants=False):

        template_contents = []

        if ascendants == False:

            template_content_links = TaxonomicRestriction.objects.get_for_taxon(TemplateContent, lazy_taxon)

            template_content_ids = template_content_links.values_list('object_id', flat=True)

            template_contents = self.filter(pk__in=template_content_ids)


        else:
            # get for all nuids, not implemented yet
            template_content_links = TaxonomicRestriction.objects.get_for_taxon_branch(TemplateContent, lazy_taxon)

            template_content_ids = template_content_links.values_list('object_id', flat=True)

            template_contents = self.filter(pk__in=template_content_ids)

        
        return template_contents


'''
    TemplateContent
    - a "hybrid" component: during build, all template contents are built for offline use
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
class TemplateContent(PublicationMixin, models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    app = models.ForeignKey(App, on_delete=models.CASCADE)

    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)

    # frontend specific assignment, e.g. home page or footer
    assignment = models.CharField(max_length=255, null=True)

    draft_template_name = models.CharField(max_length=355) # stores the actual template (e.g. .html)

    published_template = models.FileField(null=True, upload_to=get_published_page_template_path)
    published_template_definition = models.FileField(null=True, upload_to=get_published_page_template_definition_path)

    objects = TemplateContentManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # use the templates on disk
        self.draft_template = Template(self.app, self.draft_template_name, self.template_type)

        if self.published_template:
            # the published template, use the template data (definition&template) stored in the db
            self.template = Template(self.app, self.name, self.template_type,
                self.published_template.path, self.published_template_definition.path)


    # return different path for published pages
    def get_component_template(self, content_key):

        component_template_name = self.draft_template.definition['contents'][content_key]['templateName']
        # load the component template
        component_template = Template(self.app, component_template_name, 'component')

        return component_template


    def get_published_component_template(self, content_key):

        component_template_name = self.template.definition['contents'][content_key]['templateName']
        
        published_component_template_definition_filepath = self.get_published_component_template_definition_filepath(component_template_name)
        published_component_template_filepath = self.get_published_component_template_filepath(component_template_name)

        component_template = Template(self.app, component_template_name, 'component',
            template_filepath=published_component_template_filepath,
            template_definition_filepath=published_component_template_definition_filepath)

        return component_template


    # for exising published component templates. Only if the files exist on disk
    def get_published_component_template_definition_filepath(self, component_template_name):

        published_component_template_folder = self.get_published_component_template_folder(component_template_name)
        filename = '{0}.json'.format(component_template_name)
        return os.path.join(published_component_template_folder, filename)

    # ths should be adjusted to support other files (see Templates.py)
    def get_published_component_template_filepath(self, component_template_name):

        published_component_template_folder = self.get_published_component_template_folder(component_template_name)
        filename = '{0}.html'.format(component_template_name)
        return os.path.join(published_component_template_folder, filename)


    def get_published_component_template_folder(self, component_template_name):
        published_component_templates_root = get_published_component_templates_root(self)
        return os.path.join(published_component_templates_root, component_template_name)


    @property
    def name (self):
        return self.draft_template.definition['templateName']

    def get_locale(self, language_code):
        return LocalizedTemplateContent.objects.filter(template_content=self, language=language_code).first()


    def publish_assets(self):

        published_templates_root = get_published_template_content_root(self)

        if self.published_template.name and self.published_template.storage.exists(self.published_template.name):
            self.published_template.storage.delete(self.published_template.name)

        if self.published_template_definition.name and self.published_template_definition.storage.exists(self.published_template_definition.name):
            self.published_template_definition.storage.delete(self.published_template_definition.name)

        if os.path.isdir(published_templates_root):
            shutil.rmtree(published_templates_root)

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

        # store components templates
        template_definition = self.draft_template.definition

        published_templates_root = get_published_template_content_root(self)
        published_component_templates_root = os.path.join(published_templates_root, 'templates', 'component')

        for content_key, content_definition in template_definition['contents'].items():

            if content_definition['type'] == 'component':

                component_template_name = content_definition['templateName']

                component_template = self.get_component_template(content_key)

                # does not exist
                published_component_template_folder = self.get_published_component_template_folder(
                    component_template_name)

                if not os.path.isdir(published_component_template_folder):
                    os.makedirs(published_component_template_folder)

                component_template_filename = os.path.basename(component_template.template_filepath)
                component_template_definition_filename = os.path.basename(component_template.template_definition_filepath)

                published_component_template_filepath = os.path.join(published_component_template_folder,
                    component_template_filename)
                published_component_template_definition_filepath = os.path.join(published_component_template_folder,
                    component_template_definition_filename)

                print(published_component_template_definition_filepath)
                shutil.copyfile(component_template.template_filepath, published_component_template_filepath)
                shutil.copyfile(component_template.template_definition_filepath,
                    published_component_template_definition_filepath)
                


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

        primary_locale = self.get_locale(self.app.primary_language)
        if primary_locale:
            return primary_locale.draft_title
        return self.name


    class Meta:
        unique_together=('app', 'assignment')


MAX_SLUG_LENGTH = 100
class LocalizedTemplateContentManager(models.Manager):

    def create(self, creator, template_content, language, draft_title):
        
        slug = self.generate_slug(draft_title)

        localized_template_content = self.model(
            created_by = creator,
            template_content = template_content,
            language = language,
            draft_title = draft_title,
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


    def publish_components(self):

        template_definition = self.template_content.draft_template.definition

        for component_key, component_definition in template_definition['contents'].items():

            if component_definition['type'] == 'component':

                component_template = self.template_content.get_component_template(component_key)

                instances = []

                if component_definition.get('allowMultiple', False) == True:
                    instances = self.draft_contents.get(component_key, [])
                else:
                    instance = self.draft_contents.get(component_key, None)
                    if instance:
                        instances.append(instance)


                for component in instances:

                    component_uuid = component['uuid']

                    for content_key, content_definition in component_template.definition['contents'].items():
                        
                        # publish the image and add the url to the component
                        if content_definition['type'] == 'image':
                            image_type = get_component_image_type(component_key, component_uuid, content_key)

                            self.publish_images(image_type, content_definition)


    def publish_images(self, image_type, content_definition):

        content_images = []

        if content_definition.get('allowMultiple', False) == True:

            content_images = self.images(image_type=image_type)
        else:
            content_image = self.image(image_type=image_type)
            if content_image:
                content_images = [content_image]
    
        published_image_type = get_published_image_type(image_type)

        old_published_images = self.images(image_type=published_image_type)
        old_published_images.delete()

        for content_image in content_images:
            published_content_image = content_image
            published_content_image.pk = None
            published_content_image.image_type = published_image_type
            published_content_image.save()


    def publish_toplevel_images(self):

        template_definition = self.template_content.draft_template.definition
        contents = template_definition['contents']

        for content_key, content_definition in contents.items():

            if content_definition['type'] == 'image':

                image_type = content_key

                self.publish_images(image_type, content_definition)


    def publish(self):
        # set title
        self.published_title = self.draft_title
        self.published_contents = self.draft_contents

        # currently, images are not translatable. This can change in the future
        if self.language == self.template_content.app.primary_language:
            self.publish_toplevel_images()

        self.publish_components()

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


    def get_frontend_specific_url(self):
        app_settings = self.template_content.app.get_settings()

        return get_frontend_specific_url(app_settings, self)


    def get_component(self, component_key, component_uuid):

        allow_multiple = self.template_content.draft_template.definition['contents'][component_key].get(
            'allowMultiple', False)

        component = {}

        if self.draft_contents:

            if allow_multiple == True:
                
                components = self.draft_contents.get(component_key, [])

                for possible_component in components:

                    if str(possible_component['uuid']) == str(component_uuid):
                        component = possible_component
                        break

            else:
                component = self.draft_contents.get(component_key, {})

        return component


    def add_or_update_component(self, component_key, component, save=True):

        if 'uuid' not in component or not component['uuid']:
            raise ValueError('Cannot add component without uuid')

        allow_multiple = self.template_content.draft_template.definition['contents'][component_key].get(
            'allowMultiple', False)

        if not self.draft_contents:
            self.draft_contents = {}

        if allow_multiple == True:
            index = None

            if component_key not in self.draft_contents:
                self.draft_contents[component_key] = []

            for i, existing_component in enumerate(self.draft_contents[component_key], 0):
                if str(existing_component['uuid']) == str(component['uuid']):
                    index = i
                    break

            if index is not None:
                self.draft_contents[component_key][index] = component
            else:
                self.draft_contents[component_key].append(component)

        else:
            self.draft_contents[component_key] = component

        if save == True:
            self.save()


    def remove_component(self, component_key, component_uuid, save=True):

        allow_multiple = self.template_content.draft_template.definition['contents'][component_key].get(
            'allowMultiple', False)

        if not self.draft_contents:
            self.draft_contents = {}

        if allow_multiple == True:
            if component_key in self.draft_contents:

                for index, existing_component in enumerate(self.draft_contents[component_key], 0):
                    if str(existing_component['uuid']) == str(component_uuid):
                        del self.draft_contents[component_key][index]
                        break

        else:
            del self.draft_contents[component_key]

        if save == True:
            self.save()


    def get_content_image_restrictions(self, image_type):
        restrictions = {
            'allow_cropping': False,
            'allow_features': False,
        }

        return restrictions


    def __str__(self):
        return self.draft_title
        

    class Meta:
        unique_together=('template_content', 'language')



'''
    Navigations
    - TemplateContent navigation has to be fetched using the API
    - there is no offline TemplateContent navigation
    - there can be offline template content pages (e.g. landing page)
'''
class NavigationManager(models.Manager):

    def create(self, app, navigation_type, language, name):
        
        navigation = self.model(
            app = app,
            navigation_type = navigation_type,
        )
        navigation.save()

        # create the localized navigation
        localized_navigation = LocalizedNavigation.objects.create(navigation, language, name)

        return navigation


class Navigation(PublicationMixin, models.Model):

    app = models.ForeignKey(App, on_delete=models.CASCADE)
    navigation_type = models.CharField(max_length=355)
    options = models.JSONField(null=True)

    objects = NavigationManager()

    @property
    def settings(self):
        app_settings = self.app.get_settings()
        navigation_settings = app_settings['templateContent']['navigations'][self.navigation_type]
        return navigation_settings

    @property
    def toplevel_entries(self):
        return NavigationEntry.objects.filter(navigation=self, parent=None)

    def get_locale(self, language_code):
        return LocalizedNavigation.objects.filter(navigation=self, language=language_code).first()


    def publish_assets(self):
        pass


    def check_version(self):
        locales = LocalizedNavigation.objects.filter(navigation=self)
        for locale in locales:
            if locale.draft_version == locale.published_version:
                locale.save()


    def __str__(self):
        primary_locale = self.get_locale(self.app.primary_language)
        if primary_locale:
            return primary_locale.name
        else:
            return self.navigation_type

    class Meta:
        unique_together = ('app', 'navigation_type')


'''
    Localized Navigations
    - hold the published navigation
'''
class LocalizedNavigationManager(models.Manager):

    def create(self, navigation, language, name):
        
        localized_navigation = self.model(
            navigation = navigation,
            language = language,
            name = name,
        )
        localized_navigation.save()

        return localized_navigation


def travel_tree(children, path=[]):

    path_to_parent = path
    
    for counter, child in enumerate(children, 0):

        path = path_to_parent.copy()
        path.append(counter)

        navigation_entry = {
            'child': child,
            'path': path
        }

        yield navigation_entry

        if child.children:
            yield from travel_tree(child.children, path=path)


class LocalizedNavigation(models.Model):

    navigation = models.ForeignKey(Navigation, on_delete=models.CASCADE)
    language = models.CharField(max_length=15)
    name = models.CharField(max_length=355)

    draft_version = models.IntegerField(default=1)
    published_version = models.IntegerField(null=True)

    published_navigation = models.JSONField(null=True)

    objects = LocalizedNavigationManager()


    '''
    [
        {
            'linkName': 'Link Name',
            'children': [
                {
                    'linkName': 'Link Name'
                }
            ]
        }
        
    ]
    '''
    def serialize(self):

        navigation = []

        for entry in travel_tree(self.navigation.toplevel_entries):

            path = entry['path']
            localized_entry = entry['child'].get_locale(self.language)

            target_list = navigation

            for counter, index in enumerate(path, 0):

                if counter == len(path) -1:
                    serialized_entry = localized_entry.serialize()
                    target_list.insert(index, serialized_entry)
                    
                else:
                    target_list = target_list[index]['children']
            

        return navigation


    def translation_complete(self):
        
        primary_language = self.navigation.app.primary_language

        if self.language == primary_language:
            return []

        raise NotImplementedError('multilanguage navigations are not implemented yet')


    def publish(self):

        self.published_navigation = self.serialize()

        if self.published_version != self.draft_version:
            self.published_version = self.draft_version
            self.published_at = timezone.now()

        self.save(published=True)


    def save(self, *args, **kwargs):

        # indicates, if the save() command came from self.publish
        published = kwargs.pop('published', False)

        if not self.pk:

            primary_language = self.navigation.app.primary_language

            if self.language != primary_language:
                master_nav = self.navigation.get_locale(primary_language)
                self.draft_version = master_nav.draft_version

        else:

            if published == False:

                # the localized_template_content has already been published. start new version
                if self.published_version == self.draft_version:
                    self.draft_version += 1


        super().save(*args, **kwargs)


    class Meta:
        unique_together = ('navigation', 'language')


'''
    The frontend can provide urls, e.g. to identification keys or other contents
'''
class NavigationEntry(models.Model):

    navigation = models.ForeignKey(Navigation, on_delete=models.CASCADE)
    template_content = models.ForeignKey(TemplateContent, on_delete=models.CASCADE, null=True)

    position = models.IntegerField(default=1)

    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    options = models.JSONField(null=True)

    @property
    def children(self):
        return NavigationEntry.objects.filter(parent=self)

    @property
    def descendants(self):

        descendants = []

        stack = [list(self.children)]
        while stack: 
            for entry in stack.pop():
                descendants.append(entry)
                if entry.children:
                    stack.append(list(entry.children))

        return descendants


    def get_locale(self, language):
        return LocalizedNavigationEntry.objects.filter(navigation_entry=self, language=language).first()

    def __str__(self):
        primary_language = self.navigation.app.primary_language
        primary_locale = self.get_locale(primary_language)
        return primary_locale.link_name


    def save(self, *args, **kwargs):
        self.navigation.check_version()
        super().save(*args, **kwargs)


    class Meta:
        ordering=['position', 'pk'] 


class LocalizedNavigationEntry(models.Model):
    
    navigation_entry = models.ForeignKey(NavigationEntry, on_delete=models.CASCADE)
    url = models.CharField(max_length=355, null=True)
    language = models.CharField(max_length=15)
    link_name = models.CharField(max_length=355)

    def get_template_content_url(self):
        localized_template_content = self.navigation_entry.template_content.get_locale(self.language)
        return localized_template_content.get_frontend_specific_url()

    def serialize(self):

        if self.navigation_entry.template_content:
            url = self.get_template_content_url()
        else:
            url = self.url

        serialized_entry = {
            'link_name': self.link_name,
            'url': url,
            'children': [],
        }

        return serialized_entry

    class Meta:
        unique_together = ('navigation_entry', 'language')