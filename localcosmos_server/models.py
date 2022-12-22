from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db import transaction

from django.templatetags.static import static


from .taxonomy.generic import ModelWithTaxon, ModelWithRequiredTaxon
from .taxonomy.lazy import LazyAppTaxon
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey


# online ocntent
from django.template import Template, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates

from localcosmos_server.slugifier import create_unique_slug

from content_licencing.models import ContentLicenceRegistry

import uuid, os, json, shutil
    

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

    details = models.JSONField(null=True)
    
    follows = models.ManyToManyField('self', related_name='followed_by')

    is_banned = models.BooleanField(default=False)

    objects = LocalcosmosUserManager()


    # there is a bug in django for Dataset.user.on_delete=models.SET_NULL (django 3.1)
    # anonymize the datasets here instead of letting django call SET_NULL
    def anonymize_datasets(self):
        from localcosmos_server.datasets.models import Dataset
        datasets = Dataset.objects.filter(user=self)
        for dataset in datasets:
            dataset.user = None

        Dataset.objects.bulk_update(datasets, ['user'])

    # do not alter the delete method
    def delete(self, using=None, keep_parents=False):

        if settings.LOCALCOSMOS_PRIVATE == True:
            self.anonymize_datasets()
            super().delete(using=using, keep_parents=keep_parents)
        else:
            # localcosmos.org uses django-tenants
            from django_tenants.utils import schema_context, get_tenant_model
            Tenant = get_tenant_model()
            
            user_id = self.pk

            # using transactions because multiple schemas can refer to the same
            # user ID as FK references!
            with transaction.atomic():

                deleted = False
                
                # delete user and all of its data across tenants
                for tenant in Tenant.objects.all().exclude(schema_name='public'):
                    with schema_context(tenant.schema_name):

                        self.anonymize_datasets()
                        
                        super().delete(using=using, keep_parents=keep_parents)
                        # reassign the ID because delete() sets it to None
                        self.pk = user_id

                        deleted = True

                
                if deleted == False:
                    
                    # deleting from public schema is not necessary, it happens on the first schema-specific deletion
                    with schema_context('public'):
                        super().delete()
            

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
    App
    - an App is a webapp which is loaded by an index.html file
    - Apps are served by nginx or apache
'''
class AppManager(models.Manager):

    def create(self, name, primary_language, uid, **kwargs):

        app = self.model(
            name=name,
            primary_language=primary_language,
            uid=uid,
            **kwargs
        )

        app.save()

        return app
    
        
class App(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # this is the app specific subdomain on localcosmos.org/ the unzip folder on lc private
    # unique across all tenants
    uid = models.CharField(max_length=255, unique=True, editable=False)

    # automatically download app updates when you click "publish" on localcosmos.org
    # this feature is not implemented yet
    auto_update = models.BooleanField(default=True)

    primary_language = models.CharField(max_length=15)
    name = models.CharField(max_length=255)

    # the url this app is served at according to your nginx/apache setup
    # online content uses this to load a preview on the LC private installation
    url = models.URLField(null=True)

    # url for downloading the currently released apk
    apk_url = models.URLField(null=True)

    # url for downloading the currently released ipa
    # as of 2019 this does not make any sense, because apple does not support ad-hoc installations
    # for companies < 100 employees
    ipa_url = models.URLField(null=True)

    # COMMERCIAL ONLY
    # url for downloading the current webapp for installing on the private server
    pwa_zip_url = models.URLField(null=True)

    # COMMERCIAL ONLY ?
    # for version comparisons, version of the app in the appkit, version of apk, ipa and webapp might differ
    published_version = models.IntegerField(null=True)

    # an asbolute path on disk to a folder containing a www folder with static index.html file
    # online content uses published_version_path if LOCALCOSMOS_PRIVATE == True
    # online content reads templates and config files from disk
    # usually, published_version_path is settings.LOCALCOSMOS_APPS_ROOT/{App.uid}/published/www/
    # make sure published_version_path is served by your nginx/apache
    published_version_path = models.CharField(max_length=255, null=True)

    # COMMERCIAL ONLY
    # an asbolute path on disk to a folder containing a www folder with static index.html file
    # online content uses preview_version_path if LOCALCOSMOS_PRIVATE == False
    # online content reads templates and config files from disk
    # usually, preview_version_path is settings.LOCALCOSMOS_APPS_ROOT/{App.uid}/preview/www/
    # make sure preview_version_path is served by your nginx/apache
    preview_version_path = models.CharField(max_length=255, null=True)

    # COMMERCIAL ONLY
    # an asbolute path on disk to a folder containing a www folder with static index.html file
    # usually, review_version_path is settings.LOCALCOSMOS_APPS_ROOT/{App.uid}/review/www/
    # make sure review_version_path is served by your nginx/apache
    # review_version_path is used by the localcosmos_server api
    review_version_path = models.CharField(max_length=255, null=True)
    

    objects = AppManager()

    # path where the user uploads app stuff to
    # eg onlince content templates
    @property
    def media_base_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.uid)


    def get_url(self):
        if settings.LOCALCOSMOS_PRIVATE == True:
            return self.url

        # commercial installation uses subdomains
        from django_tenants.utils import get_tenant_domain_model
        Domain = get_tenant_domain_model()
        
        domain = Domain.objects.get(app=self)
        return domain.domain

    def get_admin_url(self):
        if settings.LOCALCOSMOS_PRIVATE == True:
            return reverse('appadmin:home', kwargs={'app_uid':self.uid})

        # commercial installation uses subdomains
        from django_tenants.utils import get_tenant_domain_model
        Domain = get_tenant_domain_model()
        
        domain = Domain.objects.get(app=self)
        path = reverse('appadmin:home', kwargs={'app_uid':self.uid}, urlconf='localcosmos_server.urls')

        url = '{0}{1}'.format(domain.domain, path)
        return url

    # preview is used by online content on the commercial installation only
    # on lc private, preview url is the live url
    def get_preview_url(self):
        if settings.LOCALCOSMOS_PRIVATE == True:
            return self.url

        from django_tenants.utils import get_tenant_domain_model
        Domain = get_tenant_domain_model()
        
        domain = Domain.objects.filter(tenant__schema_name='public').first()

        return '{0}.preview.{1}/'.format(self.uid, domain.domain)


    def get_installed_app_path(self, app_state):

        if settings.LOCALCOSMOS_PRIVATE == True:
            app_state = 'published'

        if app_state == 'published':
            root = self.published_version_path

            # on the first build, there is no published_version_path, but only a review_version_path
            # the "review apk" is exactly the same as the later "published apk",
            # so fall back to review settings if no published settings are available
            if root == None and settings.LOCALCOSMOS_PRIVATE == False:
                root = self.review_version_path

        elif app_state == 'preview':
            root = self.preview_version_path

        elif app_state == 'review':
            root= self.review_version_path

        else:
            raise ValueError('Invalid app_state: {0}'.format(app_state))
        
        return root

    
    # read app settings from disk, template_content
    # located at /www/settings.json, createb by AppPreviewBuilder or AppReleaseBuilder
    # app_state=='preview' or app_state=='review' are for commercial installation only
    def get_settings(self, app_state='preview'):

        root = self.get_installed_app_path(app_state)
            
        settings_json_path = os.path.join(root, 'settings.json')

        with open(settings_json_path, 'r') as settings_file:
            app_settings = json.loads(settings_file.read())

        return app_settings


    # read app features from disk, only published apps
    # app_state=='preview' or app_state=='review' are for commercial installation only
    # used eg by AppTaxonSearch.py
    def get_features(self, app_state='preview'):

        if app_state == 'preview':
            features = {}

        else:
            root = self.get_installed_app_path(app_state)
            
            features_json_path = os.path.join(root, 'localcosmos', 'features.json')

            with open(features_json_path, 'r') as features_file:
                features = json.loads(features_file.read())

        return features


    def languages(self):
        languages = [self.primary_language]
        secondary_languages = SecondaryAppLanguages.objects.filter(app=self).values_list('language_code', flat=True)
        languages += secondary_languages
        return languages
    
    def secondary_languages(self):
        return SecondaryAppLanguages.objects.filter(app=self).values_list('language_code', flat=True)


    # only published app
    def get_locale(self, key, language):
        relpath = 'locales/{0}/plain.json'.format(language)
        locale_path = os.path.join(self.published_version_path, relpath)

        if os.path.isfile(locale_path):
            with open(locale_path, 'r') as f:
                locale = json.loads(f.read())
                return locale.get(key, None)

        return None

    # LC PRIVATE: remove all contents from disk
    def delete(self, *args, **kwargs):
        app_folder = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.uid)
        if os.path.isdir(app_folder):
            shutil.rmtree(app_folder)
        super().delete(*args, **kwargs)
        

    def __str__(self):
        return self.name


class SecondaryAppLanguages(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    language_code = models.CharField(max_length=15)

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
        unique_together = ('content_type', 'object_id', 'taxon_latname', 'taxon_author')


class TaxonomicRestriction(TaxonomicRestrictionBase):
    pass




'''
    Generic Content Images
'''
class ServerContentImageMixin:

    def get_model(self):
        return ServerContentImage

    def _content_images(self, image_type='image'):

        content_type = ContentType.objects.get_for_model(self.__class__)
        ContentImageModel = self.get_model()

        self.content_images = ContentImageModel.objects.filter(content_type=content_type, object_id=self.pk,
                                                          image_type=image_type).order_by('position')

        return self.content_images

    def all_images(self):

        content_type = ContentType.objects.get_for_model(self.__class__)
        ContentImageModel = self.get_model()

        self.content_images = ContentImageModel.objects.filter(
            content_type=content_type, object_id=self.pk)

        return self.content_images

    def images(self, image_type='image'):
        return self._content_images(image_type=image_type)

    def image(self, image_type='image'):
        content_image = self._content_images(image_type=image_type).first()

        if content_image:
            return content_image

        return None

    def image_url(self, size=400):

        content_image = self.image()

        if content_image:
            return content_image.image_url(size)

        return static('noimage.png')

    # this also deletes ImageStore entries and images on disk

    def delete_images(self):

        content_type = ContentType.objects.get_for_model(self.__class__)
        ContentImageModel = self.get_model()

        content_images = ContentImageModel.objects.filter(
            content_type=content_type, object_id=self.pk)

        for image in content_images:
            # delete model db entries
            image_store = image.image_store
            image.delete()

            image_is_used = ContentImageModel.objects.filter(
                image_store=image_store).exists()

            if not image_is_used:
                image_store.delete()

    def get_content_images_primary_localization(self):

        locale = {}

        content_images = self.images()

        for content_image in content_images:

            if content_image.text and len(content_image.text) > 0:
                locale[content_image.text] = content_image.text

        return locale





def get_image_store_path(instance, filename):
    blankname, ext = os.path.splitext(filename)

    new_filename = '{0}{1}'.format(instance.md5, ext)
    path = '/'.join(['localcosmos-server', 'imagestore', '{0}'.format(instance.uploaded_by.pk),
                     new_filename])
    return path



class ImageStoreAbstract(ModelWithTaxon):

    LazyTaxonClass = LazyAppTaxon

    # null Foreignkey means the user does not exist anymore
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    
    md5 = models.CharField(max_length=255)

    # enables on delete cascade
    licences = GenericRelation(ContentLicenceRegistry)

    class Meta:
        abstract=True


class ServerImageStore(ImageStoreAbstract):
    
    source_image = models.ImageField(upload_to=get_image_store_path)



class ContentImageAbstract(models.Model):

    crop_parameters = models.TextField(null=True)

    # for things like arrows/vectors on the image
    # arrows are stored as [{"type" : "arrow" , "initialPoint": {x:1, y:1}, "terminalPoint": {x:2,y:2}, color: string}]
    features = models.JSONField(null=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField()
    content = GenericForeignKey('content_type', 'object_id')

    # a content can have different images
    # eg an image of type 'background' and an image of type 'logo'
    image_type = models.CharField(max_length=100, default='image')

    position = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    # only primary language
    text = models.CharField(max_length=355, null=True)

    # flag if a translation is needed
    requires_translation = models.BooleanField(
        default=False)  # not all images require a translation


    class Meta:
        abstract=True


import hashlib
from PIL import Image
class ContentImageProcessing:

    def get_thumb_filename(self, size=400):

        if self.image_store.source_image:
            filename = os.path.basename(self.image_store.source_image.path)
            blankname, ext = os.path.splitext(filename)

            suffix = 'uncropped'
            if self.crop_parameters:
                suffix = hashlib.md5(
                    self.crop_parameters.encode('utf-8')).hexdigest()

            feature_suffix = 'nofeatures'
            if self.features:
                features_str = json.dumps(self.features)
                feature_suffix = hashlib.md5(
                    features_str.encode('utf-8')).hexdigest()

            thumbname = '{0}-{1}-{2}-{3}{4}'.format(
                blankname, suffix, feature_suffix, size, ext)
            return thumbname

        else:
            return 'noimage.png'


    def plot_features(self, pil_image):
        raise NotImplementedError('Plotting Features not supported by LC Server')

    # apply features and cropping, return pil image
    # original_image has to be Pil.Image instance
    # CASE 1: crop parameters given.
    #   - make a canvas according to crop_parameters.width and crop_parameters.height
    #
    # CASE 2: no crop parameters given
    #   1. apply features
    #   2. thumbnail
    def get_in_memory_processed_image(self, original_image, size):

        # scale the image to match size
        original_width, original_height = original_image.size

        larger_original_side = max(original_width, original_height)
        if larger_original_side < size:
            size = larger_original_side

        # fill color for the background, if the selection expands the original image
        fill_color = (255, 255, 255, 255)

        # offset of the image on the canvas
        offset_x = 0
        offset_y = 0

        if self.crop_parameters:

            square_size = max(original_width, original_height)
            offset_x = int((square_size - original_width) / 2)
            offset_y = int((square_size - original_height) / 2)
            width = size
            height = size

            canvas = Image.new('RGBA', (square_size, square_size), fill_color)
            canvas.paste(original_image, (offset_x, offset_y))

        else:

            # define width and height
            width = size
            scaling_factor = original_width / size
            height = original_height * scaling_factor

            canvas = Image.new(
                'RGBA', (original_width, original_height), fill_color)
            canvas.paste(original_image, (offset_x, offset_y))

        # plot features and creator name
        # matplotlib is awfully slow - only use it if absolutely necessary
        if self.features:
            image_source = self.plot_features(canvas)
            canvas_with_features = Image.open(image_source)
        else:
            canvas_with_features = canvas

        # ATTENTION: crop_parameters are relative to the top-left corner of the original image
        # -> make them relative to the top left corner of square
        if self.crop_parameters:
            # {"x":253,"y":24,"width":454,"height":454,"rotate":0,"scaleX":1,"scaleY":1}
            crop_parameters = json.loads(self.crop_parameters)

            # first crop, then resize
            # box: (left, top, right, bottom)
            box = (
                crop_parameters['x'] + offset_x,
                crop_parameters['y'] + offset_y,
                crop_parameters['x'] + offset_x + crop_parameters['width'],
                crop_parameters['y'] + offset_y + crop_parameters['height'],
            )

            cropped_canvas = canvas_with_features.crop(box)

        else:
            cropped_canvas = canvas_with_features

        cropped_canvas.thumbnail([width, height], Image.ANTIALIAS)

        if original_image.format != 'PNG':
            cropped_canvas = cropped_canvas.convert('RGB')

        return cropped_canvas


    def image_url(self, size=400, force=False):

        if self.image_store.source_image.path.endswith('.svg'):
            thumburl = self.image_store.source_image.url

        else:

            image_path = self.image_store.source_image.path
            folder_path = os.path.dirname(image_path)

            thumbname = self.get_thumb_filename(size)

            thumbfolder = os.path.join(folder_path, 'thumbnails')
            if not os.path.isdir(thumbfolder):
                os.makedirs(thumbfolder)

            thumbpath = os.path.join(thumbfolder, thumbname)

            if not os.path.isfile(thumbpath) or force == True:

                original_image = Image.open(self.image_store.source_image.path)

                processed_image = self.get_in_memory_processed_image(
                    original_image, size)

                processed_image.save(thumbpath, original_image.format)

            thumburl = os.path.join(os.path.dirname(
                self.image_store.source_image.url), 'thumbnails', thumbname)

        return thumburl


class ServerContentImage(ContentImageProcessing, ContentImageAbstract):

    image_store = models.ForeignKey(ServerImageStore, on_delete=models.CASCADE)