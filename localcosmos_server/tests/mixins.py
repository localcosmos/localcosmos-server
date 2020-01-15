from localcosmos_server.models import LocalcosmosUser, App, SecondaryAppLanguages
from localcosmos_server.tests.common import TEST_MEDIA_ROOT

from localcosmos_server.datasets.models import Dataset

from localcosmos_server.tests.common import TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS

from django.utils import timezone

import os, shutil

class WithUser:

    # allowed special chars; @/./+/-/_
    test_username = 'TestUser@.+-_'
    test_email = 'testuser@localcosmos.org'
    test_password = '#$_><*}{|///0x'

    test_superuser_username = 'TestSuperuser'
    test_superuser_email = 'testsuperuser@localcosmos.org'

    test_first_name = 'First Name'

    def create_user(self):
        user = LocalcosmosUser.objects.create_user(self.test_username, self.test_email, self.test_password)
        return user
        


class WithApp:

    app_name = 'TestApp'
    app_uid = 'app_for_tests'
    app_primary_language = 'de'
    app_secondary_languages = ['en']

    testapp_relative_www_path = 'app_for_tests/published/www/'

    testapp_relative_review_www_path = 'app_for_tests/review/www/'
    testapp_relative_preview_www_path = 'app_for_tests/preview/www/'
    

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(name=self.app_name, primary_language=self.app_primary_language,
                                      uid=self.app_uid)

        for language in self.app_secondary_languages:
            secondary_language = SecondaryAppLanguages(
                app=self.app,
                language_code=language,
            )

            secondary_language.save()


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



class WithDataset:

    def create_dataset(self):

        dataset = Dataset(
            app_uuid = self.app.uuid,
            data = TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS,
            created_at = timezone.now(),
        )

        dataset.save()

        return dataset
    
