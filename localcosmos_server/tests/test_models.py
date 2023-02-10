###################################################################################################################
#
# TESTS FOR MODELS
# - this file only covers settings.LOCALCOSMOS_PRIVATE == True
#
###################################################################################################################
from django.conf import settings
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType


from localcosmos_server.models import (LocalcosmosUser, UserClients, App, AppUserRole, TaxonomicRestriction)

from localcosmos_server.datasets.models import Dataset

from localcosmos_server.taxonomy.lazy import LazyAppTaxon

from localcosmos_server.tests.common import (test_settings, test_settings_commercial, TESTAPP_NAO_RELATIVE_PATH,
                                            TESTAPP_NAO_PREVIEW_RELATIVE_PATH, TESTAPP_NAO_ABSOLUTE_PATH)
from localcosmos_server.tests.mixins import WithObservationForm, WithApp

from .mixins import WithUser, WithApp

from django.utils import timezone
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
        self.published_version_path = TESTAPP_NAO_ABSOLUTE_PATH

        self.review_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT,
                                                TESTAPP_NAO_RELATIVE_PATH)

        self.preview_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT,
                                                 TESTAPP_NAO_PREVIEW_RELATIVE_PATH)

        self.app.published_version_path = self.published_version_path
        self.app.preview_version_path = self.preview_version_path

        self.app.save()

    @test_settings
    def test_get_url(self):
        test_url = 'https://myapp.app'
        self.app.url = test_url
        self.app.save()

        url = self.app.get_url()
        self.assertEqual(url, test_url)

    @test_settings
    def test_get_admin_url(self):

        admin_url = self.app.get_admin_url()

    @test_settings
    def test_get_preview_url(self):
        test_url = 'https://myapp.app'
        self.app.url = test_url
        self.app.save()

        preview_url = self.app.get_url()
        self.assertEqual(preview_url, test_url)

    @test_settings
    def test_str(self):
        name = str(self.app)
        self.assertEqual(name, self.app.name)

    @test_settings
    def test_languages(self):
        languages = self.app.languages()

        expected_languages = set([self.app_primary_language] + self.app_secondary_languages)

        self.assertEqual(set(languages), expected_languages)

    @test_settings
    def test_secondary_languages(self):

        secondary_languages = self.app.secondary_languages()

        self.assertEqual(set(secondary_languages), set(self.app_secondary_languages))

    ###########################################################
    # all tests below require an installed app on disk
    ###########################################################

    # settings in app.published_version_path
    @test_settings
    def test_get_settings(self):
        self.assertTrue(self.app.published_version_path is not None)
        print(self.app.published_version_path)
        self.assertTrue(os.path.isdir(self.app.published_version_path))

        app_settings = self.app.get_settings()
        self.assertEqual(type(app_settings), dict)

    # features in app.published_version_path
    @test_settings
    def test_get_features(self):

        app_features = self.app.get_features()
        self.assertEqual(type(app_features), dict)


    @test_settings
    def test_get_installed_app_path(self):
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
        self.published_version_path = TESTAPP_NAO_ABSOLUTE_PATH

        self.review_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT,
                                                TESTAPP_NAO_RELATIVE_PATH)

        self.preview_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT,
                                                 TESTAPP_NAO_PREVIEW_RELATIVE_PATH)

        self.app.published_version_path = self.published_version_path
        self.app.preview_version_path = self.preview_version_path

        self.app.save()


    def publish_app(self):
        self.app.published_version_path = self.published_version_path
        self.app.save()


    def unpublish_app(self):
        self.app.published_version_path = None
        self.app.save()
        
    @test_settings_commercial
    def test_get_installed_app_path(self):
        self.publish_app()
        app_path = self.app.get_installed_app_path(app_state='published')

        self.assertEqual(app_path, self.app.published_version_path)

        self.unpublish_app()
        self.app.save()

        fallback_app_path = self.app.get_installed_app_path(app_state='published')
        self.assertEqual(fallback_app_path, self.app.review_version_path)

        preview_app_path = self.app.get_installed_app_path(app_state='preview')
        self.assertEqual(preview_app_path, self.app.preview_version_path)


    @test_settings_commercial
    def test_get_settings(self):

        preview_settings = self.app.get_settings()
        self.assertEqual(preview_settings['PREVIEW'], True)

        # the settings entry does not normally occur. It is only present for identifying
        # the settings file during this test
        review_settings = self.app.get_settings(app_state='review')
        self.assertEqual(review_settings['REVIEW'], True)
        self.assertEqual(review_settings['PREVIEW'], False)

        fallback_settings = self.app.get_settings(app_state='published')
        self.assertEqual(fallback_settings['REVIEW'], True)
        self.assertEqual(fallback_settings['PREVIEW'], False)

        self.publish_app()
        published_settings = self.app.get_settings(app_state='published')
        self.assertIn('REVIEW', published_settings)
        self.assertEqual(published_settings['PREVIEW'], False)

    @test_settings_commercial
    def test_get_features(self):

        preview_features = self.app.get_features()
        self.assertEqual(preview_features, {})

        review_features = self.app.get_features(app_state='review')
        self.assertEqual(review_features['REVIEW'], True)

        fallback_features = self.app.get_features(app_state='published')
        self.assertEqual(fallback_features['REVIEW'], True)

        self.publish_app()
        published_features = self.app.get_features(app_state='published')
        self.assertFalse('REVIEW' in published_features)
        self.assertFalse('PREVIEW' in published_features)

    
        

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

    