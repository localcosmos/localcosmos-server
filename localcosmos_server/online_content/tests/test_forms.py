from django.test import TestCase
from django.conf import settings

from localcosmos_server.tests.mixins import (WithApp, WithUser, WithOnlineContent, WithPowerSetDic,
                                             WithImageForForm)

from localcosmos_server.tests.common import test_settings

from localcosmos_server.online_content.forms import (CreateTemplateContentForm, ManageMicroContentsForm,
            ManageTemplateContentForm, DeleteMicroContentForm, UploadFileForm, UploadImageForm,
            UploadImageWithLicenceForm)

import os

# available template_type s of Flat theme
TEMPLATE_TYPES = ['page', 'feature']

class WithPublishedApp:

    # only published apps can access template content settings on lc private
    def setUp(self):
        super().setUp()
        published_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.testapp_relative_www_path)

        self.app.published_version_path = published_version_path

        self.app.save()
    

@test_settings
class TestCreateTemplateContentForm(WithPublishedApp, WithApp, TestCase):


    def test__init__(self):

        app_root = settings.LOCALCOSMOS_APPS_ROOT

        templates_root = os.path.join(self.app.published_version_path, 'themes', 'Flat', 'online_content',
                                      'templates')

        for template_type in TEMPLATE_TYPES:
            form = CreateTemplateContentForm(self.app, template_type)

            self.assertEqual(form.app, self.app)
            self.assertEqual(form.template_type, template_type)

            for choice in form.fields['template_name'].choices:

                template_path = choice[0]

                # path has to exist
                path = os.path.join(templates_root, template_path)
                
                self.assertTrue(os.path.isfile(path))


@test_settings
class TestManageMicroContentsForm(WithPublishedApp, WithApp, WithUser, WithOnlineContent, TestCase):

    test_page_microcontents = ['simple_content', 'layout1', 'layout2', 'multi-content', 'test_image', 'multi_image']
    test_page_microcontents_no_multi = ['simple_content', 'layout1', 'layout2', 'test_image']
    
    def setUp(self):
        self.user = self.create_user()
        super().setUp()

    def test__init__(self):

        template_content = self.create_template_content()
        form = ManageMicroContentsForm(template_content, language=self.app.primary_language)

        self.assertEqual(form.template_content, template_content)

        # check ALL fields of test_page.html

        for mc_type in self.test_page_microcontents:
            #field_name = 'pk-{0}-{1}'.format(self.localized_template_content.pk, mc_type)
            self.assertIn(mc_type, form.fields)

            self.assertEqual(form.fields[mc_type].language, self.app.primary_language)

        self.assertEqual(form.layoutable_simple_fields, set(['layout2']))
        self.assertEqual(form.layoutable_full_fields, set(['layout1']))
        
    # test the template test_page.html
    def test__init__for_translation(self):

        for_translation = 'en'

        template_content = self.create_template_content()
        form = ManageMicroContentsForm(template_content, language=self.app.primary_language,
                                       for_translation=for_translation)

        # check ALL fields of test_page.html

        for mc_type in self.test_page_microcontents_no_multi:
            #field_name = 'pk-{0}-{1}'.format(self.localized_template_content.pk, mc_type)
            self.assertIn(mc_type, form.fields)

            self.assertEqual(form.fields[mc_type].language, self.app.primary_language)

        self.assertEqual(form.layoutable_simple_fields, set(['layout2']))
        self.assertEqual(form.layoutable_full_fields, set(['layout1']))


@test_settings
class TestManageTemplatecontentForm(WithPublishedApp, WithApp, WithUser, WithOnlineContent, TestCase):

    def setUp(self):
        self.user = self.create_user()
        super().setUp()

    def test_append_additional_fields(self):

        template_content = self.create_template_content()

        form = ManageTemplateContentForm(template_content, language=self.app.primary_language)
        
        self.assertIn('page_flags', form.fields)
        self.assertEqual(1, len(form.fields['page_flags'].choices))
        self.assertEqual('main_navigation', form.fields['page_flags'].choices[0][0])


@test_settings
class TestDeleteMicroContentForm(WithPowerSetDic, TestCase):

    def test_validation(self):

        post_data = {
            'meta_pk' : 1,
            'localized_pk' : 2,
            'microcontent_category' : 'page',
            'microcontent_type' : 'simple_content',
        }

        # for this test case all fields are required
        required_fields = set(['meta_pk', 'localized_pk', 'microcontent_category'])

        self.validation_test(post_data, required_fields, DeleteMicroContentForm)
        

@test_settings
class TestUploadFileFormANDUploadImageForm(WithImageForForm, WithPowerSetDic, TestCase):

    def test_validation(self):

        image = self.get_image('test_image.jpg')

        post_data = {
            'pk' : 1,
            'template_content_id' : 2,
            'language' : 'en',
            'file' : image,
        }


        file_keys = ['file']

        required_fields = set(['language', 'file'])

        for form_class in [UploadFileForm, UploadImageForm]:

            self.validation_test(post_data, required_fields, form_class, file_keys=file_keys)


@test_settings    
class TestUploadImageWithLicenceForm(WithImageForForm, WithPowerSetDic, TestCase):

    def test_validation(self):

        image = self.get_image('test_image_2.jpg')

        post_data = {
            'pk' : 1,
            'template_content_id' : 2,
            'language' : 'en',
            'source_image' : image,
            'image_type' : 'test_image',
            'creator_name': 'Tester',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
        }


        file_keys = ['source_image']

        required_fields = set(['creator_name', 'licence_0', 'licence_1'])

        self.validation_test(post_data, required_fields, UploadImageWithLicenceForm, file_keys=file_keys)
