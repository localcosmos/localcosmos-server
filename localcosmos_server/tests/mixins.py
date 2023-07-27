from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.contenttypes.models import ContentType

from localcosmos_server.models import (LocalcosmosUser, App, SecondaryAppLanguages, AppUserRole, ServerImageStore,
    ServerContentImage)

from localcosmos_server.datasets.models import Dataset, DatasetImages, UserGeometry

from localcosmos_server.tests.common import (powersetdic, TEST_MEDIA_ROOT, TEST_IMAGE_PATH, TESTAPP_NAO_ABSOLUTE_PATH,
    TESTAPP_AO_ABSOLUTE_PATH, TESTAPP_NAO_UID, TESTAPP_AO_UID, TEST_OBSERVATION_FORM_JSON, DataCreator,
    TEST_OBSERVATION_FORM_POINT_JSON, TEST_CLIENT_ID, TEST_TIMESTAMP, GEOJSON_POLYGON, TEST_USER_GEOMETRY_NAME)

from django.utils import timezone

import os, shutil, json

from localcosmos_server.datasets.models import ObservationForm, Dataset


class WithUser:

    # allowed special chars; @/./+/-/_
    test_username = 'TestUser@.+-_'
    test_email = 'testuser@localcosmos.org'
    test_password = '#$_><*}{|///0x'

    test_superuser_username = 'TestSuperuser'
    test_superuser_email = 'testsuperuser@localcosmos.org'

    test_first_name = 'First Name'
    test_last_name = 'Last Name'

    def create_user(self):
        user = LocalcosmosUser.objects.create_user(self.test_username, self.test_email, self.test_password)
        return user


    def create_secondary_user(self):

        user = LocalcosmosUser.objects.create_user('secondary', 'second@ry.org', 'dsgrsg5%<>')
        return user


    def create_superuser(self):
        superuser = LocalcosmosUser.objects.create_superuser(self.test_superuser_username, self.test_superuser_email,
                                                        self.test_password)
        return superuser
        


class WithApp:

    nao_app_name = 'Test App 1'
    nao_app_uid = TESTAPP_NAO_UID

    ao_app_name = 'Test App 2'
    ao_app_uid = TESTAPP_AO_UID

    app_primary_language = 'de'
    app_secondary_languages = ['en']

    testapp_relative_www_path = 'app_for_tests/release/sources/www/'
    

    def setUp(self):
        super().setUp()

        nao_create_kwargs = {
            'published_version_path' : TESTAPP_NAO_ABSOLUTE_PATH
        }

        self.app = App.objects.create(name=self.nao_app_name, primary_language=self.app_primary_language,
                                      uid=self.nao_app_uid, **nao_create_kwargs)

        for language in self.app_secondary_languages:
            secondary_language = SecondaryAppLanguages(
                app=self.app,
                language_code=language,
            )

            secondary_language.save()


        ao_create_kwargs = {
            'published_version_path' : TESTAPP_AO_ABSOLUTE_PATH
        }

        self.ao_app = App.objects.create(name=self.ao_app_name, primary_language=self.app_primary_language,
                                        uid=self.ao_app_uid, **ao_create_kwargs)


class WithMedia:

    def clean_media(self):
        if os.path.isdir(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)

        os.makedirs(TEST_MEDIA_ROOT)  

    def setUp(self):
        super().setUp()
        self.clean_media()

    def tearDown(self):
        super().tearDown()
        self.clean_media()


class WithObservationForm:

    def setUp(self):
        super().setUp()

        with open(TEST_OBSERVATION_FORM_JSON, 'rb') as form_file:
            self.observation_form_json = json.loads(form_file.read())

        with open(TEST_OBSERVATION_FORM_POINT_JSON, 'rb') as point_form_file:
            self.observation_form_point_json = json.loads(point_form_file.read())


    def create_observation_form(self, observation_form_json=None):

        if not observation_form_json:
            observation_form_json = self.observation_form_json


        observation_form = ObservationForm(
            uuid = observation_form_json['uuid'],
            version = observation_form_json['version'],
            definition = observation_form_json
        )

        observation_form.save()

        return observation_form


    def create_dataset(self, observation_form, user=None, app=None, taxon=None):

        if app == None:
            app = self.app

        data_creator = DataCreator()

        test_data = data_creator.get_dataset_data(self.observation_form_json, taxon=taxon)

        dataset = Dataset(
            app_uuid = app.uuid,
            observation_form = observation_form,
            data = test_data,
            created_at = timezone.now(),
            client_id = TEST_CLIENT_ID,
            platform = 'browser',
            user = user,
        )

        dataset.save()

        return dataset


    def get_image_field_uuid(self, observation_form):

        field_uuid = None

        for field in observation_form.definition['fields']:
            if field['fieldClass'] == 'PictureField':
                field_uuid = field['uuid']
                break
        
        return field_uuid


    def create_dataset_image(self, dataset, image_path=TEST_IMAGE_PATH):

        image_field_uuid = self.get_image_field_uuid(dataset.observation_form)

        image = SimpleUploadedFile(name='test_image.jpg', content=open(image_path, 'rb').read(),
                                   content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset = dataset,
            field_uuid = image_field_uuid,
            image = image,
        )

        dataset_image.save()

        return dataset_image




'''
class WithDataset:

    def create_dataset(self):

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS,
            created_at = timezone.now(),
        )

        dataset.save()

        return dataset

    def create_notaxon_dataset(self):

        dataset_data = TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS
        del dataset_data['dataset']['reported_values']['7e5c9390-61cf-4cb5-8b0f-9086b2f387ce']

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = dataset_data,
            created_at = timezone.now(),
        )

        dataset.save()

        return dataset


    def create_full_dataset(self):
        
        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = TEST_DATASET_FULL_GENERIC_FORM,
            created_at = timezone.now(),
        )

        dataset.save()

        return dataset


    def create_dataset_image(self, dataset, field_uuid):

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                   content_type='image/jpeg')

        dataset_image = DatasetImages(
            dataset = dataset,
            field_uuid = field_uuid,
            image = image,
        )

        dataset_image.save()

        return dataset_image
'''
    

from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

class WithImageForForm:

    def get_image(self, filename):

        im = Image.new(mode='RGB', size=(200, 200)) # create a new image using PIL
        im_io = BytesIO() # a BytesIO object for saving image
        im.save(im_io, 'JPEG') # save the image to im_io
        im_io.seek(0) # seek to the beginning

        image = InMemoryUploadedFile(
            im_io, None, filename, 'image/jpeg', len(im_io.getvalue()), None
        )

        return image


    def get_zipfile(self, filename):

        im = Image.new(mode='RGB', size=(200, 200)) # create a new image using PIL
        im_io = BytesIO() # a BytesIO object for saving image
        im.save(im_io, 'JPEG') # save the image to im_io
        im_io.seek(0) # seek to the beginning

        zipfile = InMemoryUploadedFile(
            im_io, None, filename, 'application/zip', len(im_io.getvalue()), None
        )

        return zipfile


class WithPowerSetDic:

    def validation_test(self, post_data, required_fields, form_class, **form_kwargs):

        file_keys = form_kwargs.pop('file_keys', [])

        testcases = powersetdic(post_data)

        for post in testcases:

            files = {}
            for key, value in post.items():
                if key in file_keys:
                    files[key] = value

            form = form_class(post, files=files)
            
            keys = set(post.keys())

            form.is_valid()
            
            if required_fields.issubset(keys):
                form.is_valid()
                if not form.is_valid():
                    print(form.errors)
                self.assertEqual(form.errors, {})
                
            else:
                self.assertFalse(form.is_valid())
        
        

from localcosmos_server.datasets.models import DatasetValidationRoutine, DATASET_VALIDATION_CHOICES
class WithValidationRoutine:

    def create_validation_routine(self):

        for counter, tupl in enumerate(DATASET_VALIDATION_CHOICES, 1):

            validation_class = tupl[0]

            step = DatasetValidationRoutine(
                app=self.app,
                validation_class=validation_class,
                position=counter,
            )

            step.save()


from localcosmos_server.template_content.models import (TemplateContent, LocalizedTemplateContent)


class WithTemplateContent:

    template_content_title = 'Test template content'
    template_content_navigation_link_name = 'Test navigation link'
    template_type = 'page'
    template_name = 'page/test.html'

    def create_template_content(self, template_name=None, template_type=None):

        if template_name == None:
            template_name = self.template_name

        if template_type == None:
            template_type = self.template_type
        
        self.template_content = TemplateContent.objects.create(self.user, self.app, self.app.primary_language,
                self.template_content_title, self.template_content_navigation_link_name, self.template_name,
                self.template_type)

        self.localized_template_content = LocalizedTemplateContent.objects.get(language=self.app.primary_language,
            template_content=self.template_content)

        return self.template_content


    def create_secondary_language_ltcs(self):

        for language in self.app.secondary_languages():

            draft_title = '{0} {1}'.format(self.template_content_title, language)
            draft_navigation_link_name = '{0} {1}'.format(self.template_content_navigation_link_name, language)

            localized_template_content = LocalizedTemplateContent.objects.create(self.user, self.template_content,
                language, draft_title, draft_navigation_link_name)

    def get_view(self, view_class, url_name):
        
        url_kwargs = self.get_url_kwargs()
        
        request = self.factory.get(reverse(url_name, kwargs=url_kwargs))
        request.session = self.client.session
        request.app = self.app
        request.user = self.user

        view = view_class()
        view.request = request
        view.app = self.app
        view.app_disk_path = self.app.get_installed_app_path(app_state='published')
        view.kwargs = url_kwargs

        return view, request
        

class CommonSetUp:
    
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        self.user = self.create_user()

        self.role = AppUserRole(
            app=self.app,
            user = self.user,
            role='admin',
        )

        self.superuser = self.create_superuser()

        self.role.save()

        self.client.login(username=self.test_superuser_username, password=self.test_password)


class WithUserGeometry:

    def create_user_geometry(self, user, geometry=GEOJSON_POLYGON, name=TEST_USER_GEOMETRY_NAME):

        geojson = json.dumps(GEOJSON_POLYGON['geometry'])

        user_geometry = UserGeometry(
            user=user,
            geometry=geojson,
            name=name,
        )

        user_geometry.save()

        return user_geometry


class WithServerContentImage:

    def get_content_image(self, user, instance, image_type='image', crop_parameters=None):

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')
        
        image_store = ServerImageStore(
            source_image = image,
            uploaded_by = user,
        )

        image_store.save()

        content_image = ServerContentImage(
            image_store = image_store,
            content_type = ContentType.objects.get_for_model(instance),
            object_id = instance.id,
            image_type = image_type,
        )

        if crop_parameters:
            content_image.crop_parameters = crop_parameters

        content_image.save()

        return content_image
