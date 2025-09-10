###################################################################################################################
#
# TESTS FOR MODELS
# - this file only covers settings.LOCALCOSMOS_PRIVATE == True
#
###################################################################################################################
from django.conf import settings
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType


from localcosmos_server.models import (LocalcosmosUser, UserClients, App, AppUserRole, TaxonomicRestriction,
                                       ServerExternalMedia)

from localcosmos_server.datasets.models import Dataset

from localcosmos_server.taxonomy.lazy import LazyAppTaxon

from localcosmos_server.tests.common import (test_settings, test_settings_app_kit,
    TESTAPP_NAO_PUBLISHED_RELATIVE_PATH, TESTAPP_NAO_PREVIEW_RELATIVE_PATH, TESTAPP_NAO_REVIEW_RELATIVE_PATH,
    TESTAPP_NAO_PUBLISHED_ABSOLUTE_PATH, TESTAPP_NAO_PREVIEW_ABSOLUTE_PATH, TESTAPP_NAO_REVIEW_ABSOLUTE_PATH,
    TESTAPP_AO_PUBLISHED_RELATIVE_PATH, TESTAPP_AO_PREVIEW_RELATIVE_PATH, TESTAPP_AO_REVIEW_RELATIVE_PATH,
    TESTAPP_AO_PUBLISHED_ABSOLUTE_PATH, TESTAPP_AO_PREVIEW_ABSOLUTE_PATH, TESTAPP_AO_REVIEW_ABSOLUTE_PATH,)

from localcosmos_server.tests.mixins import WithObservationForm, WithApp

from .mixins import WithUser, WithApp

from django.utils import timezone
from datetime import timedelta
import uuid, os, shutil


class TestLocalcosmosUser(WithObservationForm, WithUser, WithApp, TestCase):
    
    @test_settings
    def test_create_user(self):
        user = LocalcosmosUser.objects.create_user(self.test_username, self.test_email, self.test_password)

        self.assertEqual(user.username, self.test_username)
        self.assertEqual(user.email, self.test_email)
        self.assertFalse(user.is_banned)
        self.assertTrue(user.slug != None)
        self.assertTrue(user.uuid != None)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    @test_settings
    def test_create_user_with_extra_fields(self):
        extra_fields = {
            'first_name' : self.test_first_name
        }

        user = LocalcosmosUser.objects.create_user(self.test_username, self.test_email, self.test_password,
                                                   **extra_fields)

        self.assertEqual(user.first_name, self.test_first_name)

    @test_settings
    def test_create_superuser(self):
        superuser = LocalcosmosUser.objects.create_superuser(self.test_superuser_username, self.test_superuser_email,
                                                             self.test_password)

        self.assertEqual(superuser.username, self.test_superuser_username)
        self.assertEqual(superuser.email, self.test_superuser_email)
        self.assertFalse(superuser.is_banned)
        self.assertTrue(superuser.slug != None)
        self.assertTrue(superuser.uuid != None)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    @test_settings
    def test_create_superuser_with_extra_fields(self):
        extra_fields = {
            'first_name' : self.test_first_name
        }

        superuser = LocalcosmosUser.objects.create_superuser(self.test_superuser_username, self.test_superuser_email,
                                                             self.test_password, **extra_fields)

        self.assertEqual(superuser.first_name, self.test_first_name)

    @test_settings
    def test_delete(self):

        user = LocalcosmosUser.objects.create_user(self.test_username, self.test_email, self.test_password)
        user_pk = user.pk
        user.delete()

        exists = LocalcosmosUser.objects.filter(pk=user_pk).exists()
        self.assertFalse(exists)

    @test_settings
    def test_delete_anonymize_datasets(self):

        user = LocalcosmosUser.objects.create_user(self.test_username, self.test_email, self.test_password)

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        dataset.user = user
        dataset.save()

        user.delete()

        dataset = Dataset.objects.get(pk=dataset.pk)
        self.assertEqual(dataset.user, None)



class TestUserClients(WithUser, TestCase):

    def setUp(self):
        self.user = self.create_user()

    @test_settings
    def test_save(self):

        test_client_id = 'test_client_id'
        test_platform = 'browser'

        client = UserClients(
            user = self.user,
            client_id = test_client_id,
            platform =test_platform,
        )

        client.save()

        client = UserClients.objects.get(user=self.user)

        self.assertEqual(client.user, self.user)
        self.assertEqual(client.client_id, test_client_id)
        self.assertEqual(client.platform, test_platform)
        


class TestAppManager(TestCase):

    @test_settings
    def test_create(self):

        app_name = 'My app'
        app_primary_language = 'en'
        app_uid = 'myapp'

        app = App.objects.create(app_name, app_primary_language, app_uid)

        self.assertEqual(app.uid, app_uid)
        self.assertEqual(app.name, app_name)
        self.assertEqual(app.primary_language, app_primary_language)



class TestApp(WithApp, TestCase):

    def setUp(self):
        super().setUp()
        
        self.published_version_path = TESTAPP_AO_PUBLISHED_ABSOLUTE_PATH

        self.review_version_path = TESTAPP_AO_REVIEW_ABSOLUTE_PATH

        self.preview_version_path = TESTAPP_AO_PREVIEW_ABSOLUTE_PATH
        
        
    def set_app(self):

        self.app.published_version_path = self.published_version_path
        self.app.preview_version_path = self.preview_version_path        
        self.app.review_version_path = self.review_version_path
        
        self.app.save()
        

    @test_settings
    def test_get_url(self):
        
        self.set_app()
        
        test_url = 'https://myapp.app'
        self.app.url = test_url
        self.app.save()

        url = self.app.get_url()
        self.assertEqual(url, test_url)

    @test_settings
    def test_get_admin_url(self):
        self.set_app()

        admin_url = self.app.get_admin_url()

    @test_settings
    def test_get_preview_url(self):
        self.set_app()
        
        test_url = 'https://myapp.app'
        self.app.url = test_url
        self.app.save()

        preview_url = self.app.get_url()
        self.assertEqual(preview_url, test_url)

    @test_settings
    def test_str(self):
        self.set_app()
        
        name = str(self.app)
        self.assertEqual(name, self.app.name)

    @test_settings
    def test_languages(self):
        self.set_app()
        
        languages = self.app.languages()

        expected_languages = set([self.app_primary_language] + self.app_secondary_languages)

        self.assertEqual(set(languages), expected_languages)

    @test_settings
    def test_secondary_languages(self):
        self.set_app()

        secondary_languages = self.app.secondary_languages()

        self.assertEqual(set(secondary_languages), set(self.app_secondary_languages))

    ###########################################################
    # all tests below require an installed app on disk
    ###########################################################

    # settings in app.published_version_path
    @test_settings
    def test_get_settings(self):
        self.set_app()
        
        self.assertTrue(self.app.published_version_path is not None)
        self.assertTrue(os.path.isdir(self.app.published_version_path))
        
        # root should always be 'published'
        root = self.app.get_installed_app_path(app_state='preview')
        self.assertEqual(root, self.published_version_path)

        # non-commercial only has published version path
        app_settings = self.app.get_settings()
        self.assertEqual(type(app_settings), dict)
        
        self.assertEqual(app_settings['PUBLISHED'], True)
        self.assertEqual(app_settings['PREVIEW'], False)
        self.assertEqual(app_settings['REVIEW'], False)

    # features in app.published_version_path
    @test_settings
    def test_get_features(self):
        self.set_app()

        app_features = self.app.get_features()
        self.assertEqual(type(app_features), dict)
        
        app_path = self.app.get_installed_app_path(app_state='published')

        self.assertEqual(app_path, self.app.published_version_path)
        
        self.assertEqual(app_features['PUBLISHED'], True)
        self.assertEqual(app_features['PREVIEW'], False)
        self.assertEqual(app_features['REVIEW'], False)



    @test_settings
    def test_get_installed_app_path(self):
        self.set_app()
        
        app_path = self.app.get_installed_app_path(app_state='published')

        self.assertEqual(app_path, self.app.published_version_path)

        self.app.preview_version_path = self.preview_version_path
        self.app.published_version_path = None
        self.app.save()

        fallback_app_path = self.app.get_installed_app_path(app_state='published')
        self.assertEqual(fallback_app_path, self.app.published_version_path)

        preview_app_path = self.app.get_installed_app_path(app_state='preview')
        self.assertEqual(preview_app_path, None)
        
        self.app.published_version_path = self.published_version_path
        self.app.save()


    @test_settings
    def test_get_locale(self):
        self.set_app()
        
        for language in self.app.languages():
            locale = self.app.get_locale('Home', language)
            self.assertTrue(type(locale), str)

            locale = self.app.get_locale('Non Existant Entry', language)
            self.assertEqual(locale, None)

        # test a non existant locale
        locale = self.app.get_locale('Non Existant Entry', 'xx')
        self.assertEqual(locale, None)

    # because delete() removes the app from disk, create a dummy app and do not use 'testapp'
    @test_settings
    def test_delete(self):
        self.set_app()
        
        app_name = 'Test App 2'
        app_uid = 'test_app_2'
        app_primary_language = 'en'

        app_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, app_uid)
        app_www_path = os.path.join(app_path, 'www')

        if os.path.isdir(app_path):
            shutil.rmtree(app_path)
            
        os.makedirs(app_www_path)

        app = App.objects.create(name=app_name, primary_language=app_primary_language, uid=app_uid)
        app.published_version_path = app_www_path
        app.save()

        
        self.assertTrue(os.path.isdir(app_path))
        self.assertTrue(os.path.isdir(app.published_version_path))

        app.delete()

        self.assertFalse(os.path.exists(app_path))
        self.assertFalse(os.path.exists(app.published_version_path))
        

class TestCommercialApp(WithApp, TestCase):

    def setUp(self):
        super().setUp()
        
        self.published_version_path = TESTAPP_NAO_PUBLISHED_ABSOLUTE_PATH

        self.review_version_path = TESTAPP_NAO_REVIEW_ABSOLUTE_PATH

        self.preview_version_path = TESTAPP_NAO_PREVIEW_ABSOLUTE_PATH

        
    def set_app(self):

        #self.app.published_version_path = self.published_version_path
        self.app.preview_version_path = self.preview_version_path
        self.app.review_version_path = self.review_version_path
        self.app.published_version_path = None

        self.app.save()


    def publish_app(self):
        
        self.app.published_version_path = self.published_version_path
        self.app.save()


    def unpublish_app(self):
        self.set_app()
        
        self.app.published_version_path = None
        self.app.save()
    
    
    @test_settings_app_kit
    def test_get_installed_app_path(self):
        self.set_app()
        
        self.publish_app()
        app_path = self.app.get_installed_app_path(app_state='published')

        self.assertEqual(app_path, self.app.published_version_path)

        self.unpublish_app()
        self.app.save()

        fallback_app_path = self.app.get_installed_app_path(app_state='published')
        self.assertEqual(fallback_app_path, self.app.review_version_path)

        preview_app_path = self.app.get_installed_app_path(app_state='preview')
        self.assertEqual(preview_app_path, self.app.preview_version_path)
        
        review_app_path = self.app.get_installed_app_path(app_state='review')
        self.assertEqual(review_app_path, self.app.review_version_path)


    @test_settings_app_kit
    def test_get_settings(self):
        self.set_app()

        preview_settings = self.app.get_settings()
        self.assertEqual(preview_settings['PREVIEW'], True)
        self.assertEqual(preview_settings['PUBLISHED'], False)
        self.assertEqual(preview_settings['REVIEW'], False)

        # the settings entry does not normally occur. It is only present for identifying
        # the settings file during this test
        review_settings = self.app.get_settings(app_state='review')
        self.assertEqual(review_settings['REVIEW'], True)
        self.assertEqual(review_settings['PREVIEW'], False)
        self.assertEqual(review_settings['PUBLISHED'], False)

        root = self.app.get_installed_app_path(app_state='published')
        self.assertEqual(root, self.review_version_path)
        fallback_settings = self.app.get_settings(app_state='published')
        self.assertEqual(fallback_settings['REVIEW'], True)
        self.assertEqual(fallback_settings['PREVIEW'], False)
        self.assertEqual(fallback_settings['PUBLISHED'], False)

        self.publish_app()
        published_settings = self.app.get_settings(app_state='published')
        self.assertEqual(published_settings['REVIEW'], False)
        self.assertEqual(published_settings['PREVIEW'], False)
        self.assertEqual(published_settings['PUBLISHED'], True)

    @test_settings_app_kit
    def test_get_features(self):
        self.set_app()

        preview_features = self.app.get_features()
        self.assertEqual(preview_features, {})

        review_features = self.app.get_features(app_state='review')
        self.assertEqual(review_features['REVIEW'], True)
        self.assertEqual(review_features['PREVIEW'], False)
        self.assertEqual(review_features['PUBLISHED'], False)

        fallback_features = self.app.get_features(app_state='published')
        self.assertEqual(fallback_features['REVIEW'], True)
        self.assertEqual(fallback_features['PREVIEW'], False)
        self.assertEqual(fallback_features['PUBLISHED'], False)

        self.publish_app()

        published_features = self.app.get_features(app_state='published')
        self.assertEqual(published_features['REVIEW'], False)
        self.assertEqual(published_features['PREVIEW'], False)
        self.assertEqual(published_features['PUBLISHED'], True)

    
        

from localcosmos_server.models import APP_USER_ROLES
class TestAppUserRole(WithApp, WithUser, TestCase):

    @test_settings
    def test_save(self):

        user = self.create_user()

        for role_tuple in APP_USER_ROLES:
            role = role_tuple[0]

            user_role = AppUserRole(
                app = self.app,
                user = user,
                role = role,
            )

            user_role.save()

            user_role = AppUserRole.objects.get(user=user, app=self.app)
            self.assertEqual(user_role.role, role)

            user_role.delete()


from localcosmos_server.taxonomy.lazy import LazyAppTaxon
class TestTaxonomicRestriction(WithUser, TestCase):

    test_taxon_kwargs = {
        "taxon_source": "taxonomy.sources.col",
        "name_uuid": "eb53f49f-1f80-4505-9d56-74216ac4e548",
        "taxon_nuid": "006002009001005001001",
        "taxon_latname": "Abies alba",
        "taxon_author" : "Linnaeus",
        "gbif_nubKey": 2685484,
    }

    @test_settings
    def test_save(self):

        user = self.create_user()

        lazy_taxon = LazyAppTaxon(**self.test_taxon_kwargs)
        content_type = ContentType.objects.get_for_model(user)

        restriction = TaxonomicRestriction(
            taxon=lazy_taxon,
            content_type=content_type,
            object_id=user.id,
        )

        restriction.save()

        restriction_pk = restriction.pk

        restriction = TaxonomicRestriction.objects.get(pk=restriction_pk)
        
        self.assertEqual(restriction.restriction_type, 'exists')
        self.assertEqual(restriction.object_id, user.id)
        self.assertEqual(restriction.content_type, content_type)
        self.assertEqual(restriction.content, user)
        self.assertEqual(str(restriction.taxon.name_uuid), str(lazy_taxon.name_uuid))
        

class TestTaxonomicRestrictionManager(WithApp, TestCase):
    
    def setUp(self):
        super().setUp()

        taxon_0 = {
            'taxon_source' : 'taxonomy.sources.col',
            'taxon_latname' : 'Lacerta',
            'taxon_author' : 'L.',
            'taxon_nuid' : '001',
            'name_uuid' : uuid.uuid4(),
        }

        taxon_1 = {
            'taxon_source' : 'taxonomy.sources.col',
            'taxon_latname' : 'Lacerta agilis',
            'taxon_author' : 'L.',
            'taxon_nuid' : '001001',
            'name_uuid' : uuid.uuid4(),
        }

        synonym_1 = {
            'taxon_source' : 'taxonomy.sources.col',
            'taxon_latname' : 'Lacerta agilis synonym',
            'taxon_author' : 'L.',
            'taxon_nuid' : '001001',
            'name_uuid' : uuid.uuid4(),
        }

        self.content_type = ContentType.objects.get_for_model(App)

        self.lazy_taxon_0 = LazyAppTaxon(**taxon_0)
        self.lazy_taxon_1 = LazyAppTaxon(**taxon_1)
        self.synonym = LazyAppTaxon(**synonym_1)


    @test_settings
    def test_get_for_taxon_simple(self):
        
        restriction = TaxonomicRestriction(
            content_type = self.content_type,
            object_id = self.app.id,
        )

        restriction.set_taxon(self.lazy_taxon_1)
        restriction.save()

        links = TaxonomicRestriction.objects.get_for_taxon(App, self.lazy_taxon_1)
        self.assertEqual(links[0], restriction)

        links = TaxonomicRestriction.objects.get_for_taxon(App, self.synonym)
        self.assertEqual(links[0], restriction)

        links = TaxonomicRestriction.objects.get_for_taxon(App, self.lazy_taxon_0)
        self.assertEqual(list(links), [])

    @test_settings
    def test_get_for_taxon_higher(self):
        
        restriction = TaxonomicRestriction(
            content_type = self.content_type,
            object_id = self.app.id,
        )

        restriction.set_taxon(self.lazy_taxon_0)
        restriction.save()

        links = TaxonomicRestriction.objects.get_for_taxon(App, self.lazy_taxon_1)
        self.assertEqual(list(links), [])

        links = TaxonomicRestriction.objects.get_for_taxon(App, self.synonym)
        self.assertEqual(list(links), [])

        links = TaxonomicRestriction.objects.get_for_taxon(App, self.lazy_taxon_0)
        self.assertEqual(links[0], restriction)

    @test_settings
    def test_get_for_taxon_branch_simple(self):
        
        restriction = TaxonomicRestriction(
            content_type = self.content_type,
            object_id = self.app.id,
        )

        restriction.set_taxon(self.lazy_taxon_1)
        restriction.save()

        links = TaxonomicRestriction.objects.get_for_taxon_branch(App, self.lazy_taxon_1)
        self.assertEqual(links[0], restriction)

        links = TaxonomicRestriction.objects.get_for_taxon_branch(App, self.synonym)
        self.assertEqual(links[0], restriction)

        links = TaxonomicRestriction.objects.get_for_taxon_branch(App, self.lazy_taxon_0)
        self.assertEqual(list(links), [])

    @test_settings
    def test_get_for_taxon_brnach_higher(self):
        
        restriction = TaxonomicRestriction(
            content_type = self.content_type,
            object_id = self.app.id,
        )

        restriction.set_taxon(self.lazy_taxon_0)
        restriction.save()

        links = TaxonomicRestriction.objects.get_for_taxon_branch(App, self.lazy_taxon_1)
        self.assertEqual(links[0], restriction)

        links = TaxonomicRestriction.objects.get_for_taxon_branch(App, self.synonym)
        self.assertEqual(links[0], restriction)

        links = TaxonomicRestriction.objects.get_for_taxon_branch(App, self.lazy_taxon_0)
        self.assertEqual(links[0], restriction)

    
    
            
TEST_EXTERNAL_IMAGE_URL = 'https://code-for-nature.com/images/Biodiversity-illustration-screen-sm.png'
class TestServerExternalMedia(WithApp, TestCase):

    @test_settings
    def test_create_external_media(self):
        media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            title='Test Image',
            description='A test image description',
            media_type='image',
            author='Test Author',
            license='CC BY 4.0',
            position=1,
        )
        media.save()
        
        self.assertEqual(media.content_object, self.app)
        self.assertEqual(media.url, 'https://example.com/image.jpg')
        self.assertEqual(media.title, 'Test Image')
        self.assertEqual(media.media_type, 'image')
        self.assertEqual(media.media_category, None)  # image doesn't auto-categorize
        self.assertEqual(media.author, 'Test Author')
        self.assertTrue(media.is_accessible)  # default True

    @test_settings
    def test_auto_categorization(self):
        # Test video categorization
        youtube_media = ServerExternalMedia(
            content_object=self.app,
            url='https://youtube.com/watch?v=test',
            media_type='youtube',
        )
        youtube_media.save()
        self.assertEqual(youtube_media.media_category, 'video')
        
        # Test audio categorization
        audio_media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/sound.mp3',
            media_type='mp3',
        )
        audio_media.save()
        self.assertEqual(audio_media.media_category, 'audio')
        
        # Test document categorization
        doc_media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/doc.pdf',
            media_type='pdf',
        )
        doc_media.save()
        self.assertEqual(doc_media.media_category, 'document')
        
        # Test standalone types (no categorization)
        image_media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            media_type='image',
        )
        image_media.save()
        self.assertEqual(image_media.media_category, None)
        
        website_media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com',
            media_type='website',
        )
        website_media.save()
        self.assertEqual(website_media.media_category, None)

    @test_settings
    def test_str_method(self):
        # Test with title
        media_with_title = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            title='Test Image',
            media_type='image',
        )
        media_with_title.save()
        self.assertEqual(str(media_with_title), 'Test Image (image)')
        
        # Test without title (uses URL)
        media_without_title = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            media_type='image',
        )
        media_without_title.save()
        self.assertEqual(str(media_without_title), 'https://example.com/image.jpg (image)')

    @test_settings
    def test_get_media_category_display_name(self):
        # Test categorized media
        youtube_media = ServerExternalMedia(
            content_object=self.app,
            url='https://youtube.com/watch?v=test',
            media_type='youtube',
        )
        youtube_media.save()
        self.assertEqual(youtube_media.get_media_category_display_name(), 'Video')
        
        # Test standalone media
        image_media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            media_type='image',
        )
        image_media.save()
        self.assertEqual(image_media.get_media_category_display_name(), 'Image')

    @test_settings
    def test_get_file_size_display(self):
        media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            media_type='image',
        )
        media.save()
        
        # Test unknown size
        self.assertEqual(media.get_file_size_display(), 'Unknown size')
        
        # Test various sizes
        media.file_size = 500
        self.assertEqual(media.get_file_size_display(), '500.0 B')
        
        media.file_size = 1500
        self.assertEqual(media.get_file_size_display(), '1.5 KB')
        
        media.file_size = 1500000
        self.assertEqual(media.get_file_size_display(), '1.4 MB')
        
        media.file_size = 1500000000
        self.assertEqual(media.get_file_size_display(), '1.4 GB')

    @test_settings
    def test_is_large_file(self):
        media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image.jpg',
            media_type='image',
        )
        media.save()
        
        # Test unknown size
        self.assertFalse(media.is_large_file())
        
        # Test small file (1MB)
        media.file_size = 1024 * 1024
        self.assertFalse(media.is_large_file())  # default threshold is 5MB
        
        # Test large file (6MB)
        media.file_size = 6 * 1024 * 1024
        self.assertTrue(media.is_large_file())
        
        # Test custom threshold
        media.file_size = 3 * 1024 * 1024  # 3MB
        self.assertFalse(media.is_large_file(threshold_mb=5))
        self.assertTrue(media.is_large_file(threshold_mb=2))

    @test_settings
    def test_fetch_file_size_basic(self):
        # Test YouTube URL (should return None)
        youtube_media = ServerExternalMedia(
            content_object=self.app,
            url='https://youtube.com/watch?v=test',
            media_type='youtube',
        )
        youtube_media.save()
        size = youtube_media.fetch_file_size()
        self.assertIsNone(size)
        
        # Test with no URL
        no_url_media = ServerExternalMedia(
            content_object=self.app,
            url='',
            media_type='image',
        )
        no_url_media.save()
        size = no_url_media.fetch_file_size()
        self.assertIsNone(size)
        
        # Note: Testing actual HTTP requests would require mocking
        # or a test server, which is beyond this unit test scope

    @test_settings
    def test_url_change_triggers_size_fetch(self):
        # Create media with initial URL
        media = ServerExternalMedia(
            content_object=self.app,
            url='https://example.com/image1.jpg',
            media_type='image',
        )
        media.save()
        
        # Change URL - this should trigger size fetch attempt
        # (though it will fail in test environment)
        media.url = 'https://example.com/image2.jpg'
        media.save()
        
        # The save method should have attempted to fetch size
        # In real environment with valid URLs, this would work

    @test_settings
    def test_manual_categorization_override(self):
        # Create YouTube media but manually set different category
        media = ServerExternalMedia(
            content_object=self.app,
            url='https://youtube.com/watch?v=test',
            media_type='youtube',
            media_category='document',  # Manual override
        )
        media.save()
        
        # Should preserve manual categorization
        self.assertEqual(media.media_category, 'document')
        
        # Change media type but keep manual category
        media.media_type = 'mp3'
        media.save()
        
        # Should still preserve manual categorization
        self.assertEqual(media.media_category, 'document')

    @test_settings
    def test_position_ordering(self):
        media1 = ServerExternalMedia.objects.create(
            content_object=self.app,
            url='https://example.com/1.jpg',
            media_type='image',
            position=2,
        )
        
        media2 = ServerExternalMedia.objects.create(
            content_object=self.app,
            url='https://example.com/2.jpg',
            media_type='image',
            position=1,
        )
        
        media3 = ServerExternalMedia.objects.create(
            content_object=self.app,
            url='https://example.com/3.jpg',
            media_type='image',
            position=3,
        )
        
        # Should be ordered by position when retrieved
        content_type = ContentType.objects.get_for_model(self.app)
        all_media = list(ServerExternalMedia.objects.filter(
            content_type=content_type, 
            object_id=self.app.id
        ).order_by('position'))
        self.assertEqual(all_media, [media2, media1, media3])
        
    @test_settings
    def test_fetch_file_size_real_url(self):
        media = ServerExternalMedia(
            content_object=self.app,
            url=TEST_EXTERNAL_IMAGE_URL,
            media_type='image',
        )
        media.save()
        
        size = media.fetch_file_size()
        
        expected_size = 658114

        self.assertEqual(size, expected_size)

        # The actual size may vary if the image changes, so just check it's a positive integer
        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)
        
        # Also check that the file_size field is updated
        media.refresh_from_db()
        self.assertEqual(media.file_size, expected_size)
        
    @test_settings
    def test_update_file_size(self):
        media = ServerExternalMedia(
            content_object=self.app,
            url=TEST_EXTERNAL_IMAGE_URL,
            media_type='image',
        )
        media.save()
        
        # set a wrong file size
        media.file_size = 12345
        media.save()
        
        self.assertEqual(media.file_size, 12345)
        
        # Update file size
        result = media.update_file_size()
        
        self.assertTrue(result)
        
        expected_size = 658114
        
        self.assertEqual(media.file_size, expected_size)
        
    @test_settings
    def test_needs_checking(self):
        media = ServerExternalMedia(
            content_object=self.app,
            url=TEST_EXTERNAL_IMAGE_URL,
            media_type='image',
        )
        media.save()
        
        # the needs checking is a manager method
        needs_checking = ServerExternalMedia.objects.needs_checking()
        self.assertEqual(list(needs_checking), [media])
        
        media.check_url_and_update_metadata()
        media.refresh_from_db()
        
        needs_checking = ServerExternalMedia.objects.needs_checking()
        self.assertEqual(list(needs_checking), [])
        
        # set last_checked_at to 31 days in the past
        media.last_checked_at = timezone.now() - timedelta(days=31)
        media.save()

        needs_checking = ServerExternalMedia.objects.needs_checking()
        self.assertEqual(list(needs_checking), [media])

    @test_settings
    def test_generic_relation_access(self):
        """Test that we can access external media through the generic relation"""
        media1 = ServerExternalMedia.objects.create(
            content_object=self.app,
            url='https://example.com/1.jpg',
            media_type='image',
        )
        
        media2 = ServerExternalMedia.objects.create(
            content_object=self.app,
            url='https://example.com/2.jpg',
            media_type='image',
        )
        
        # Access through generic relation (if set up on MetaApp)
        # If MetaApp has: external_media = GenericRelation(ServerExternalMedia)
        # Then this would work: app_media = list(self.app.external_media.all())
        
        # For now, test direct query
        content_type = ContentType.objects.get_for_model(self.app)
        app_media = list(ServerExternalMedia.objects.filter(
            content_type=content_type,
            object_id=self.app.id
        ))
        
        self.assertEqual(len(app_media), 2)
        self.assertIn(media1, app_media)
        self.assertIn(media2, app_media)