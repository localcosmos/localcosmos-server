from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse


from .taxonomy.generic import ModelWithRequiredTaxon
from .taxonomy.lazy import LazyAppTaxon
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


# online ocntent
from django.template import Template, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates

from localcosmos_server.slugifier import create_unique_slug

import uuid, os, json

class LocalcosmosUserManager(UserManager):
    
    def create_user(self, username, email, password, **extra_fields):
        slug = create_unique_slug(username, 'slug', self.model)

        extra_fields.update({
            'slug' : slug,
        })

        user = super().create_user(username, email, password, **extra_fields)
        
        return user

    def create_superuser(self, username, email, password, **extra_fields):

        slug = create_unique_slug(username, 'slug', self.model)

        extra_fields.update({
            'slug' : slug,
        })

        superuser = super().create_superuser(username, email, password, **extra_fields)

        return superuser


class LocalcosmosUser(AbstractUser):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    slug = models.SlugField(unique=True)

    details = JSONField(null=True)

    # moved to details JSONField
    #name_on_gbif = models.BooleanField(default=False, verbose_name=_("Publish first and last name on GBIF?"))
    #default_content_licence = models.CharField(max_length=255, choices=LICENCE_CHOICES,
    #                                           default=settings.CONTENT_LICENCING_DEFAULT_LICENCE)
    #accept_messages = models.BooleanField(default=True)
    
    follows = models.ManyToManyField('self', related_name='followed_by')

    is_banned = models.BooleanField(default=False)

    objects = LocalcosmosUserManager()

    class Meta:
        unique_together = ('email',)


'''
    CLIENTS // DEVICES
    - a client can be used by several users, eg if one logs out and another one logs in on a device
    - the client/user combination is unique
'''
'''
    platform is sent by the platform the app was used on
'''
class UserClients(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=255)
    platform = models.CharField(max_length=255)

    class Meta:
        unique_together = ('user', 'client_id')



'''
    an App is a webapp which is loaded by an index.html file
    - Apps are served by nginx or apache
'''
class AppManager(models.Manager):

    def create(self, name, primary_language, uid):

        # circular import
        app = self.model(
            name=name,
            primary_language=primary_language,
            uid=uid,
        )

        app.save()

        return app
        
class App(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # this is the app specific subdomain on localcosmos.org/ the unzip folder on lc private
    # unique across all tenants
    uid = models.CharField(max_length=255, unique=True, editable=False)

    # automatically download app updates when you click "publish" on localcosmos.org
    auto_update = models.BooleanField(default=True)

    primary_language = models.CharField(max_length=15)
    name = models.CharField(max_length=255)

    # the url this app is served at according to your nginx/apache setup
    # online content uses this to load a preview on the open source installation
    url = models.URLField(null=True)

    # download the currently released apk here
    apk_url = models.URLField(null=True)

    # download currently released ipa here
    ipa_url = models.URLField(null=True)

    # download current webapp for installing on the private server
    pwa_zip_url = models.URLField(null=True)
    
    # for version comparisons, version for apk, ipa and webapp
    published_version = models.IntegerField(null=True)

    # an asbolute path on disk to a folder containing a www folder with static index.html file
    # online content uses published_version_path if LOCALCOSMOS_OPEN_SOURCE == True
    # online content reads templates and config files from disk
    # usually, published_version_path is settings.LOCALCOSMOS_APPS_ROOT/{App.uid}/live/www/
    # make sure published_version_path is served by your nginx/apache
    published_version_path = models.CharField(max_length=255, null=True)

    # COMMERCIAL ONLY
    # an asbolute path on disk to a folder containing a www folder with static index.html file
    # online content uses preview_version_path if LOCALCOSMOS_OPEN_SOURCE == False
    # online content reads templates and config files from disk
    # usually, preview_version_path is settings.LOCALCOSMOS_APPS_ROOT/{App.uid}/preview/www/
    # make sure preview_version_path is served by your nginx/apache
    preview_version_path = models.CharField(max_length=255, null=True)

    # COMMERCIAL ONLY
    # an asbolute path on disk to a folder containing a www folder with static index.html file
    # usually, review_version_path is settings.LOCALCOSMOS_APPS_ROOT/{App.uid}/preview/www/
    # make sure review_version_path is served by your nginx/apache
    # review_version_path is used by the localcosmos_server api
    review_version_path = models.CharField(max_length=255, null=True)
    

    objects = AppManager()


    def get_url(self):
        if settings.LOCALCOSMOS_OPEN_SOURCE == True:
            return self.url

        # commercial installation uses subdomains
        from lcsite.models import Domain
        domain = Domain.objects.get(app=self)
        return domain.domain

    def get_admin_url(self):
        if settings.LOCALCOSMOS_OPEN_SOURCE == True:
            return reverse('appadmin:home', kwargs={'app_uid':self.uid})

        # commercial installation uses subdomains
        from lcsite.models import Domain
        domain = Domain.objects.get(app=self)
        path = reverse('appadmin:home', kwargs={'app_uid':self.uid}, urlconf='localcosmos_server.urls')

        url = '{0}{1}'.format(domain.domain, path)
        return url

    # preview is used by online content on the commercial installation only
    # on open source, preview url is the live url
    def get_preview_url(self):
        if settings.LOCALCOSMOS_OPEN_SOURCE == True:
            return self.url

        from lcsite.models import Domain
        domain = Domain.objects.filter(tenant__schema_name='public').first()
        return '{0}{1}{2}/preview/www/'.format(domain.domain, settings.APP_KIT_PREVIEW_URL, self.uid)


    # read app settings from disk, online_content
    # preview=True is for commercial installation only
    def get_settings(self, preview=True):

        if settings.LOCALCOSMOS_OPEN_SOURCE == True:
            preview = False
        
        root = self.published_version_path
        if preview == True:
            root = self.preview_version_path
            
        settings_json_path = os.path.join(root, 'settings.json')

        with open(settings_json_path, 'r') as settings_file:
            app_settings = json.loads(settings_file.read())

        return app_settings


    # read app features from disk, only published apps
    # preview=True is for commercial installation only
    def get_features(self, preview=True):
        root = self.published_version_path
        
        features_json_path = os.path.join(root, 'features.json')

        with open(features_json_path, 'r') as features_file:
            features = json.loads(features_file.read())

        return features

    # api_settings is used by localcosmos_server.api, eg to determine allow_anonymous_observations
    # api_settings only contains settings which make sense for the api (need_to_know basis)
    # review=True is for commercial installation only
    def get_api_settings(self, review=False):

        if settings.LOCALCOSMOS_OPEN_SOURCE == True:
            review = False
        
        root = self.published_version_path

        # on the first build, there is no published_version_path, but only a review_version_path
        # the "review apk" es exactly the same as the later "published apk", so fall back to review settings if no published settings are available
        if review == True or root == None:
            root = self.review_version_path

        api_settings_json_path = os.path.join(root, 'api', 'settings.json')

        with open(api_settings_json_path, 'r') as api_settings_file:
            api_settings = json.loads(api_settings_file.read())

        return api_settings


    def languages(self):
        languages = [self.primary_language]
        secondary_languages = SecondaryAppLanguages.objects.filter(app=self).values_list('language_code', flat=True)
        languages += secondary_languages
        return languages
    
    def secondary_languages(self):
        return SecondaryAppLanguages.objects.filter(app=self).values_list('language_code', flat=True)

    ##############################################################################################################
    # theme
    def get_installed_app_path(self):
        if self.preview_version_path:
            return self.preview_version_path

        return self.published_version_path

    def get_theme_path(self, preview=True):
        
        app_settings = self.get_settings(preview=preview)
        
        theme_name = app_settings['THEME']
        installed_app_path = self.get_installed_app_path()
        return os.path.join(installed_app_path, 'themes', theme_name)

    def get_theme_config(self, preview=True):

        theme_path = self.get_theme_path(preview=preview)
        theme_config_path = os.path.join(theme_path, 'config.json')

        with open(theme_config_path, 'r') as theme_config_file:
            theme_config = json.loads(theme_config_file.read())

        return theme_config
        
    ###############################################################################################################
    # online content specific
    
    def get_online_content_templates_path(self, preview=True):
        app_theme_path = self.get_theme_path(preview=preview)
        return os.path.join(app_theme_path, 'online_content', 'templates')


    # return the online_content specific theme settings
    # called from online_content.api.views and online_content.models.TemplateContentFlagsManager
    def get_online_content_settings(self, preview=True):
        theme_config = self.get_theme_config(preview=preview)

        oc_settings = theme_config['online_content']
        return oc_settings
    
    # return a list of available templates, always use the live version, used by eg online_content.forms.CreateTemplateContentForm
    # eg displays a selection in the AppAdmin
    def get_online_content_templates(self, template_type):

        # preview is always false for this
        preview = False
        
        templates_path = os.path.join(self.get_online_content_templates_path(preview=preview), template_type)
        oc_settings = self.get_online_content_settings(preview=preview)
        language = self.primary_language

        templates = []
    
        for filename in os.listdir(templates_path):

            template_path = '%s/%s' % (template_type, filename)
            verbose_name = template_path

            if template_path in oc_settings['verbose_template_names'] and language in oc_settings['verbose_template_names'][template_path]:
                verbose_name = oc_settings['verbose_template_names'][template_path][language]

            templates.append((template_path, verbose_name))

        return templates


    def get_online_content_template(self, template_name, preview=True):
        # return an instance of Template
        # Template(contents, origin, origin.template_name, self.engine,)
        # contents is the content of the .html file
        # origin is an Origin instance
        # engine is a template engine
        # Template can be instantiated directly, ony with contents

        theme_path = self.get_theme_path(preview=preview)
        online_content_path = os.path.join(theme_path, 'online_content')

        template_path = os.path.join(online_content_path, 'templates', template_name)

        templates_base_dir = os.path.join(online_content_path, 'templates')
        params = {
            'NAME' : 'OnlineContentEngine',
            #'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [templates_base_dir],
            'APP_DIRS': False,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
                'loaders' : [
                    'django.template.loaders.filesystem.Loader',
                ]
            },
        }
        engine = DjangoTemplates(params)

        try:
            with open(template_path, encoding=engine.engine.file_charset) as fp:
                contents = fp.read()
        except FileNotFoundError:
            msg = 'Online Content Template %s does not exist. Tried: %s' % (template_name, template_path)
            raise TemplateDoesNotExist(msg)

        # use the above engine with dirs
        template = Template(contents, engine=engine.engine)
        return template

    # only published app
    def get_locale(self, key, language):
        relpath = 'locales/{0}/plain.json'.format(language)
        locale_path = os.path.join(self.published_version_path, relpath)

        if os.path.isfile(locale_path):
            with open(locale_path, 'r') as f:
                locale = json.loads(f.read())
                return locale.get(key, None)

        return None
        

    def __str__(self):
        return self.name


class SecondaryAppLanguages(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    language_code = models.CharField(max_length=15, choices=settings.LANGUAGES)

    class Meta:
        unique_together = ('app', 'language_code')



APP_USER_ROLES = (
    ('admin',_('admin')), # can do everything
    ('expert',_('expert')), # can validate datasets (Expert Review)
)
class AppUserRole(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    role = models.CharField(max_length=60, choices=APP_USER_ROLES)

    def __str__(self):
        return '%s' % (self.role)

    class Meta:
        unique_together = ('user', 'app')
    

'''
    Taxonomic Restrictions
'''
TAXONOMIC_RESTRICTION_TYPES = (
    ('exists', _('exists')),
    ('required', _('required')),
    ('optional', _('optional')),
)
class TaxonomicRestrictionBase(ModelWithRequiredTaxon):

    LazyTaxonClass = LazyAppTaxon

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField()
    content = GenericForeignKey('content_type', 'object_id')

    restriction_type = models.CharField(max_length=100, choices=TAXONOMIC_RESTRICTION_TYPES, default='exists')

    def __str__(self):
        return self.taxon_latname

    class Meta:
        abstract = True
        unique_together = ('content_type', 'object_id', 'taxon_uuid')


class TaxonomicRestriction(TaxonomicRestrictionBase):
    pass
