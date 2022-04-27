from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings

from localcosmos_server.models import SecondaryAppLanguages

from localcosmos_server.online_content.views import (ManageOnlineContent, CreateTemplateContent, ManageMicroContents,
    ManageTemplateContent, TranslateTemplateContent, PublishTemplateContent, DeleteTemplateContent,
    UnpublishTemplateContent, DeleteMicroContent, DeleteFileContent, UploadFile, UploadImage, ManageImageUpload,
    GetFormField)

from localcosmos_server.online_content.mixins import OnlineContentMixin

from localcosmos_server.online_content.models import (TemplateContent, LocalizedDraftTextMicroContent,
                DraftTextMicroContent, TemplateContentFlags, LocalizedTemplateContent, DraftImageMicroContent,
                LocalizedDraftImageMicroContent)

from localcosmos_server.online_content.forms import ManageTemplateContentForm, TranslateTemplateContentForm


from localcosmos_server.tests.mixins import (WithDataset, WithApp, WithUser, WithMedia, WithOnlineContent,
                                             CommonSetUp, WithImageForForm)

from localcosmos_server.tests.common import test_settings, MockPost

import os

class WithPublishedApp:

    # only published apps can access template content settings on lc private
    def setUp(self):
        super().setUp()
        published_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.testapp_relative_www_path)

        self.app.published_version_path = published_version_path

        self.app.save()
        

@test_settings
class TestManageOnlineContent(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, TestCase):


    def get_url_kwargs(self):
        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        return url_kwargs
    

    def test_get_context_data(self):

        self.create_template_content()
        
        view, request = self.get_view(ManageOnlineContent, 'manage_onlinecontent')

        context = view.get_context_data(**{})
        self.assertEqual(list(context['features']), [])
        self.assertEqual(context['pages'].first(), self.template_content)
        
    def test_get(self):

        url_kwargs = self.get_url_kwargs()
        response = self.client.get(reverse('manage_onlinecontent', kwargs=url_kwargs))

        self.assertEqual(response.status_code, 200)


@test_settings
class TestCreateTemplateContent(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, TestCase):


    def get_post_data(self):
        
        post_data = {
            'draft_title' : 'Test draft title',
            'draft_navigation_link_name' : 'Test link name',
            'template_name' : 'page/test.html',
            'template_type' : 'page',
            'input_language' : self.app.primary_language
        }

        return post_data
    

    def get_url_kwargs(self):
        
        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_type' : 'page', 
        }

        return url_kwargs
    

    def test_get_context_data(self):

        
        view, request = self.get_view(CreateTemplateContent, 'create_template_content')

        context = view.get_context_data(**{})

        self.assertEqual(context['template_type'], 'page')
        

    def test_get_form_kwargs(self):

        
        view, request = self.get_view(CreateTemplateContent, 'create_template_content')

        form_kwargs = view.get_form_kwargs(**{})

        self.assertEqual(form_kwargs['language'], self.app.primary_language)
        

    def test_get_form(self):

        
        view, request = self.get_view(CreateTemplateContent, 'create_template_content')

        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)
        

    def test_form_valid(self):

        post_data = self.get_post_data()

        view, request = self.get_view(CreateTemplateContent, 'create_template_content')

        form = view.form_class(self.app, view.kwargs['template_type'], data=post_data,
                               **view.get_form_kwargs())

        form.is_valid()

        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)

        self.assertEqual(response.status_code, 302)

        created_tc = TemplateContent.objects.filter(app=self.app, template_name=post_data['template_name'],
                                                 template_type=post_data['template_type']).first()


        self.assertEqual(created_tc.__class__, TemplateContent)
        

    def test_get(self):

        response = self.client.get(reverse('create_template_content', kwargs=self.get_url_kwargs()))

        self.assertEqual(response.status_code, 200)
        

    def test_post(self):

        post_data = self.get_post_data()

        response = self.client.post(reverse('create_template_content', kwargs=self.get_url_kwargs()), post_data)

        self.assertEqual(response.status_code, 302)

        created_tc = TemplateContent.objects.filter(app=self.app, template_name=post_data['template_name'],
                                                 template_type=post_data['template_type']).first()


        self.assertEqual(created_tc.__class__, TemplateContent)


class ManageMicroContentsMixin:

    cms_fields = ['simple_content', 'layout1', 'layout2', 'multi-content']

    app_secondary_languages = ['en', 'fr']

    def get_post_data(self):
        post_data = {
            'draft_title' : 'Test draft title - edited',
            'draft_navigation_link_name' : 'Test link name - edited',
            'page_flags' : [],
            'simple_content' : 'Test simple content',
            'layout1' : '<b>layout 1</b>',
            'layout2' : '<ul><li>layout 2</li></ul>',
            'multi-content' : ['a', 'b', 'c'],
            'input_language' : self.app.primary_language
        }

        return post_data
    

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk' : self.template_content.pk, 
        }

        return url_kwargs


    def validate_saved_microcontents(self, template_content, form, language=None):

        if language is None:
            language = self.app.primary_language
        
        for field_ in form:

            field = field_.field

            if field_.name in self.cms_fields:
                self.assertTrue(hasattr(field, 'cms_object'))

                data = form.cleaned_data[field_.name]

                if field_.name == 'multi-content':

                    for counter, content in enumerate(data, 0):
                        created_meta_instance = field.cms_object.Model.objects.filter(
                            template_content=template_content,
                            microcontent_type=field.cms_object.microcontent_type).order_by('pk')[counter]
                        
                        self.assertTrue(created_meta_instance is not None)

                        created_content = created_meta_instance.get_content(language)
                        self.assertEqual(created_content, content)
                        locale = created_meta_instance.get_localized(language)
                        self.assertEqual(locale.creator, self.user)

                else:
                    created_meta_instance = field.cms_object.Model.objects.get(
                        template_content=template_content, microcontent_type=field.cms_object.microcontent_type)

                    self.assertTrue(created_meta_instance is not None)

                    created_content = created_meta_instance.get_content(language)
                    self.assertEqual(created_content, data)
                    locale = created_meta_instance.get_localized(language)
                    self.assertEqual(locale.creator, self.user)
    
    
@test_settings
class TestManageMicroContents(ManageMicroContentsMixin, WithPublishedApp, CommonSetUp, WithUser, WithApp,
                              WithOnlineContent, WithMedia, TestCase):
        
    def test_dispatch(self):

        template_content = self.create_template_content()

        view, request = self.get_view(ManageMicroContents, 'manage_template_content')

        view.form_class = ManageTemplateContentForm

        response = view.dispatch(request, **self.get_url_kwargs())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.language, self.app.primary_language)

    def test_set_template_content(self):

        template_content = self.create_template_content()

        view, request = self.get_view(ManageMicroContents, 'manage_template_content')

        url_kwargs = self.get_url_kwargs()

        view.set_template_content(request, **url_kwargs)

        self.assertEqual(view.template_content, template_content)

    def test_set_language(self):
        template_content = self.create_template_content()

        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content

        url_kwargs = self.get_url_kwargs()

        view.set_language(request, **url_kwargs)

        self.assertEqual(view.language, self.app.primary_language)
        

    def test_get_context_data(self):

        template_content = self.create_template_content()

        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm

        context = view.get_context_data(**{})
        self.assertEqual(context['language'], self.app.primary_language)
        self.assertEqual(context['template_content'], template_content)


    def validate_saved_content(self, view, template_content, field, data, user):

        created_meta_instance = field.cms_object.Model.objects.filter(template_content=template_content,
                    microcontent_type=field.cms_object.microcontent_type).order_by('pk').last()

        self.assertTrue(created_meta_instance is not None)

        created_content = created_meta_instance.get_content(self.app.primary_language)
        self.assertEqual(created_content, data)
        locale = created_meta_instance.get_localized(self.app.primary_language)
        self.assertEqual(locale.creator, self.user)
        
    def test_save_content(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm

        post = MockPost(self.get_post_data())
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        for field_ in form:

            field = field_.field

            if field_.name in self.cms_fields:
                self.assertTrue(hasattr(field, 'cms_object'))

                data = form.cleaned_data[field_.name]

                if field_.name == 'multi-content':

                    for content in data:

                        view._save_content(template_content, self.app.primary_language, field, content, self.user)
                        self.validate_saved_content(view, template_content, field, content, self.user)

                else:
                    view._save_content(template_content, self.app.primary_language, field, data, self.user)
                    self.validate_saved_content(view, template_content, field, data, self.user)
                    

    def test_get_form_kwargs(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm

        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['language'], self.app.primary_language)
        

    def test_get_form(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm

        form = view.get_form()

        self.assertEqual(form.__class__, view.form_class)
        

    def test_get_form_force_initial(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm

        form_initial = view.get_form_force_initial()

        self.assertEqual(form_initial.__class__, view.form_class)
        self.assertEqual(form_initial.is_bound, False)
        
    # save primary ltc, unready all translations
    def test_save_localized_template_content(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.form_class = ManageTemplateContentForm

        localized_template_content = template_content.get_localized(self.app.primary_language)
        localized_template_content.translation_ready = True
        localized_template_content.save()

        secondary_languages = self.app.secondary_languages()

        self.assertTrue(len(secondary_languages) > 0)

        self.create_secondary_language_ltcs()
        
        for language in secondary_languages:

            ltc = template_content.get_localized(language)
            ltc.translation_ready = True
            ltc.save()


        view.language = self.app.primary_language

        post_data = self.get_post_data()
        post = MockPost(post_data)
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.localized_template_content = localized_template_content
        view.save_localized_template_content(form)

        localized_template_content.refresh_from_db()
        self.assertEqual(localized_template_content.draft_title, post_data['draft_title'])
        self.assertEqual(localized_template_content.draft_navigation_link_name,
                         post_data['draft_navigation_link_name'])

        self.assertFalse(localized_template_content.translation_ready)

        for language in secondary_languages:

            ltc = template_content.get_localized(language)
            self.assertFalse(ltc.translation_ready)


    # save secondary ltc, unready only submitted language
    def test_save_secondary_localized_template_content(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.form_class = ManageTemplateContentForm

        primary_ltc = template_content.get_localized(self.app.primary_language)
        primary_ltc.translation_ready = True
        primary_ltc.save()

        secondary_languages = self.app.secondary_languages()

        self.assertTrue(len(secondary_languages) > 0)

        self.create_secondary_language_ltcs()
        
        for language in secondary_languages:

            ltc = template_content.get_localized(language)
            ltc.translation_ready = True
            ltc.save()

        test_language = secondary_languages[0]
        
        view.language = test_language

        post_data = self.get_post_data()
        post = MockPost(post_data)
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        localized_template_content = template_content.get_localized(test_language)
        view.localized_template_content = localized_template_content
        view.save_localized_template_content(form)

        self.assertEqual(localized_template_content.draft_title, post_data['draft_title'])
        self.assertEqual(localized_template_content.draft_navigation_link_name,
                         post_data['draft_navigation_link_name'])

        self.assertFalse(localized_template_content.translation_ready)

        primary_ltc.refresh_from_db()
        self.assertTrue(primary_ltc.translation_ready)

        for language in secondary_languages:

            if language != test_language:
                ltc = template_content.get_localized(language)
                self.assertTrue(ltc.translation_ready)

                    
    def test_save_microcontent_fields(self):

        template_content = self.create_template_content()
        view, request = self.get_view(ManageMicroContents, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm

        post_data = self.get_post_data()
        post = MockPost(post_data)
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.save_microcontent_fields(form)

        self.validate_saved_microcontents(template_content, form)


        # test deletion of meta instance
        # edit the post data

        post_data['simple_content'] = ''
        post = MockPost(post_data)
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        field = form.fields['simple_content']

        qry = field.cms_object.Model.objects.filter(template_content=template_content,
                                                    microcontent_type=field.cms_object.microcontent_type)

        self.assertTrue(qry.exists())

        view.save_microcontent_fields(form)

        self.assertFalse(qry.exists())
        

        # test deletion of localized instances        
        layout_1 = 'layout1'
        secondary_language = 'fr'
        field = form.fields[layout_1]
        
        layout_1_qry = field.cms_object.Model.objects.filter(template_content=template_content,
                                                             microcontent_type=field.cms_object.microcontent_type)

        # creater translatoin of layout1
        LocaleModel = field.cms_object.Model.get_locale_model()

        localized_draft_microcontent = LocaleModel.objects.create(layout_1_qry.first(), secondary_language,
                                                                  'test fr', self.user)
        
        localized_qry = LocalizedDraftTextMicroContent.objects.filter(microcontent=layout_1_qry.first(),
                                                                      language=secondary_language)

        self.assertTrue(layout_1_qry.exists())

        self.assertTrue(localized_qry.exists())
        
        post_data[layout_1] = ''
        post_data['input_language'] = secondary_language
        post = MockPost(post_data)
        form = view.form_class(template_content, post, for_translation=True, language=secondary_language)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.save_microcontent_fields(form, for_translation=True)

        self.assertTrue(layout_1_qry.exists())

        self.assertFalse(localized_qry.exists())        
        

    def test_post_form_invalid(self):
        # a required field is 'draft_title'

        template_content = self.create_template_content()

        post_data = self.get_post_data()
        del post_data['draft_title']

        response = self.client.post(reverse('manage_template_content', kwargs=self.get_url_kwargs()), post_data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data['saved_as_draft'])
        self.assertFalse(response.context_data['form'].is_valid())


    def validate_valid_post(self, response, template_content):
        self.assertEqual(response.context_data['form'].errors, {})
        self.assertEqual(response.context_data['form'].data, {})
        self.assertFalse(response.context_data['form'].is_bound)
        self.assertEqual(response.context_data['language'], self.app.primary_language)
        self.assertEqual(response.context_data['template_content'], template_content)
        

    def test_post_form_valid_secondary_languages_present(self):

        template_content = self.create_template_content()

        post_data = self.get_post_data()

        response = self.client.post(reverse('manage_template_content', kwargs=self.get_url_kwargs()), post_data)

        self.validate_valid_post(response, template_content)
        self.assertTrue(response.context_data['saved_as_draft'])


    def test_post_form_valid_translation_ready_secondary_languages_present_no_translation_errors(self):

        template_content = self.create_template_content()

        # create test_image and multi_image
        self.create_draft_image_microcontent(template_content, 'test_image', self.app.primary_language)
        self.create_draft_image_microcontent(template_content, 'multi_image', self.app.primary_language)

        post_data = self.get_post_data()

        url = '{0}?translation-ready=1'.format(reverse('manage_template_content', kwargs=self.get_url_kwargs()))
        response = self.client.post(url, post_data)

        self.validate_valid_post(response, template_content)
        self.assertFalse(response.context_data['saved_as_draft'])
        self.assertTrue(response.context_data['tried_translation_ready'])
        self.assertEqual(response.context_data['translation_errors'], [])

        # no translation errors
        ltc = template_content.get_localized(self.app.primary_language)
        self.assertTrue(ltc.translation_ready)


    def test_post_form_valid_translation_ready_secondary_languages_present_with_translation_errors(self):

        template_content = self.create_template_content()

        post_data = self.get_post_data()

        url = '{0}?translation-ready=1'.format(reverse('manage_template_content', kwargs=self.get_url_kwargs()))
        response = self.client.post(url, post_data)

        self.validate_valid_post(response, template_content)
        self.assertFalse(response.context_data['saved_as_draft'])
        self.assertTrue(response.context_data['tried_translation_ready'])
        self.assertEqual(len(response.context_data['translation_errors']), 2)

        # translation errors: 2 images are missing
        ltc = template_content.get_localized(self.app.primary_language)
        self.assertFalse(ltc.translation_ready)
        

    def test_post_form_valid_translation_ready_no_secondary_languages_present_no_publication_errors(self):

        for language in SecondaryAppLanguages.objects.filter(app=self.app):
            language.delete()

        template_content = self.create_template_content()

        # create test_image and multi_image
        self.create_draft_image_microcontent(template_content, 'test_image', self.app.primary_language)
        self.create_draft_image_microcontent(template_content, 'multi_image', self.app.primary_language)

        post_data = self.get_post_data()

        url = '{0}?translation-ready=1'.format(reverse('manage_template_content', kwargs=self.get_url_kwargs()))
        response = self.client.post(url, post_data)

        self.validate_valid_post(response, template_content)
        self.assertFalse(response.context_data['saved_as_draft'])
        self.assertTrue(response.context_data['tried_publication'])
        self.assertEqual(response.context_data['publication_errors'], [])

        # no publication errors
        ltc = template_content.get_localized(self.app.primary_language)
        self.assertEqual(ltc.published_version, 1)


    def test_post_form_valid_translation_ready_no_secondary_languages_present_with_publication_errors(self):

        for language in SecondaryAppLanguages.objects.filter(app=self.app):
            language.delete()

        template_content = self.create_template_content()

        post_data = self.get_post_data()

        url = '{0}?translation-ready=1'.format(reverse('manage_template_content', kwargs=self.get_url_kwargs()))
        response = self.client.post(url, post_data)

        self.validate_valid_post(response, template_content)
        self.assertFalse(response.context_data['saved_as_draft'])
        self.assertTrue(response.context_data['tried_publication'])
        self.assertEqual(len(response.context_data['publication_errors']), 2)

        # no publication errors
        ltc = template_content.get_localized(self.app.primary_language)
        self.assertEqual(ltc.published_version, None)


@test_settings
class TestManageTemplateContent(ManageMicroContentsMixin, WithPublishedApp, CommonSetUp, WithUser, WithApp,
                                WithOnlineContent, TestCase):

    def test_dispatch(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        view, request = self.get_view(ManageTemplateContent, 'manage_template_content')

        view.form_class = ManageTemplateContentForm

        response = view.dispatch(request, **self.get_url_kwargs())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.language, self.app.primary_language)
        self.assertEqual(view.localized_template_content, ltc)


    def test_get_context_data(self):

        template_content = self.create_template_content()
        localized_template_content = template_content.get_localized(self.app.primary_language)

        view, request = self.get_view(ManageTemplateContent, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm
        view.localized_template_content = localized_template_content

        context = view.get_context_data(**{})
        self.assertEqual(context['localized_template_content'], localized_template_content)
        self.assertIn('/online-content/{0}'.format(localized_template_content.slug), context['preview_url'])
        self.assertTrue(context['preview'])


    def test_get_initial(self):

        template_content = self.create_template_content()
        localized_template_content = template_content.get_localized(self.app.primary_language)

        view, request = self.get_view(ManageTemplateContent, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm
        view.localized_template_content = localized_template_content

        initial = view.get_initial()

        self.assertEqual(initial['draft_title'], localized_template_content.draft_title)
        self.assertEqual(initial['draft_navigation_link_name'],
                         localized_template_content.draft_navigation_link_name)
        self.assertEqual(initial['input_language'], localized_template_content.language)
        self.assertEqual(initial['page_flags'], [])


    def test_form_valid(self):

        template_content = self.create_template_content()
        localized_template_content = template_content.get_localized(self.app.primary_language)

        view, request = self.get_view(ManageTemplateContent, 'manage_template_content')
        view.template_content = template_content
        view.language = self.app.primary_language
        view.form_class = ManageTemplateContentForm
        view.localized_template_content = localized_template_content

        post_data = self.get_post_data()
        post_data['page_flags'] = ['main_navigation']

        post = MockPost(post_data)
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.form_valid(form)

        self.validate_saved_microcontents(template_content, form)

        # validate page flag add
        flag = TemplateContentFlags.objects.filter(template_content=self.template_content)
        self.assertEqual(flag.first().flag, 'main_navigation')


        # test flag deletion
        post_data['page_flags'] = []

        post = MockPost(post_data)
        form = view.form_class(template_content, post)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.form_valid(form)
        self.assertFalse(flag.exists())
        

@test_settings
class TestTranslateTemplateContent(ManageMicroContentsMixin, WithPublishedApp, CommonSetUp, WithUser, WithApp,
                                   WithOnlineContent, TestCase):

    def setUp(self):
        super().setUp()
        self.secondary_language = self.app_secondary_languages[0]
        
    def get_url_kwargs(self):

        url_kwargs = super().get_url_kwargs()

        url_kwargs['language'] = self.secondary_language

        return url_kwargs

    def test_dispatch(self):
        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.secondary_language)

        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')

        view.form_class = TranslateTemplateContentForm

        response = view.dispatch(request, **self.get_url_kwargs())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.template_content, self.template_content)
        self.assertEqual(view.language, self.secondary_language)
        self.assertEqual(view.localized_template_content, None)


    def test_get_context_data(self):

        template_content = self.create_template_content()

        primary_ltc = template_content.get_localized(self.app.primary_language)
        
        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')
        view.template_content = template_content
        view.language = self.secondary_language
        view.form_class = TranslateTemplateContentForm
        view.localized_template_content = None

        context = view.get_context_data(**{})
        self.assertEqual(context['localized_template_content'], None)
        self.assertEqual(context['source_page'], primary_ltc)
        self.assertTrue(context['preview'])

    def test_get_initial_no_ltc(self):

        template_content = self.create_template_content()

        primary_ltc = template_content.get_localized(self.app.primary_language)
        
        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')
        view.template_content = template_content
        view.language = self.secondary_language
        view.form_class = TranslateTemplateContentForm
        view.localized_template_content = None

        initial = view.get_initial()
        self.assertEqual(initial, {})
        

    def test_get_initial_with_ltc(self):

        template_content = self.create_template_content()

        localized_title = 'draft title en'
        localized_link_name = 'draft navigation link name en'

        secondary_ltc = LocalizedTemplateContent.objects.create( self.user, template_content,
                                            self.secondary_language, localized_title, localized_link_name)

        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')
        view.template_content = template_content
        view.language = self.secondary_language
        view.form_class = TranslateTemplateContentForm
        view.localized_template_content = secondary_ltc

        initial = view.get_initial()
        self.assertEqual(initial['draft_title'], localized_title)
        self.assertEqual(initial['draft_navigation_link_name'], localized_link_name)


    def test_get_form_kwargs(self):

        template_content = self.create_template_content()

        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')
        view.template_content = template_content
        view.language = self.secondary_language
        view.form_class = TranslateTemplateContentForm
        view.localized_template_content = None

        form_kwargs = view.get_form_kwargs()
        self.assertTrue(form_kwargs['for_translation'])


    def test_get_form_force_initial(self):

        template_content = self.create_template_content()

        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')
        view.template_content = template_content
        view.language = self.secondary_language
        view.form_class = TranslateTemplateContentForm
        view.localized_template_content = None

        form = view.get_form_force_initial()
        self.assertFalse(form.is_bound)
        self.assertEqual(form.data, {})


    def test_form_valid(self):

        template_content = self.create_template_content()

        view, request = self.get_view(TranslateTemplateContent, 'translate_template_content')
        view.template_content = template_content
        view.language = self.secondary_language
        view.form_class = TranslateTemplateContentForm
        view.localized_template_content = None

        post_data = self.get_post_data()
        post_data['input_language'] = self.secondary_language
        post = MockPost(post_data)
        form = view.form_class(template_content, post, for_translation=True)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.form_valid(form)

        ltc = template_content.get_localized(self.secondary_language)
        self.assertEqual(ltc.draft_title, post_data['draft_title'])
        self.assertEqual(ltc.draft_navigation_link_name, post_data['draft_navigation_link_name'])

        self.validate_saved_microcontents(template_content, form, language=self.secondary_language)

        # test with existing ltc
        post_data['simple_content'] = 'edited simple content'
        post_data['draft_title'] = 'edited draft title'

        view.localized_template_content = ltc

        post = MockPost(post_data)
        form = view.form_class(template_content, post, for_translation=True)

        form.is_valid()

        self.assertEqual(form.errors, {})

        view.form_valid(form)

        ltc.refresh_from_db()

        self.assertEqual(ltc.draft_title, post_data['draft_title'])
        self.assertEqual(ltc.draft_navigation_link_name, post_data['draft_navigation_link_name'])

        self.validate_saved_microcontents(template_content, form, language=self.secondary_language)


@test_settings
class TestPublishTemplateContent(ManageMicroContentsMixin, WithPublishedApp, CommonSetUp, WithUser, WithApp,
                                 WithOnlineContent, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
        }

        return url_kwargs

    def test_dispatch(self):

        template_content = self.create_template_content()
        view, request = self.get_view(PublishTemplateContent, 'publish_template_content')

        response = view.dispatch(request, **self.get_url_kwargs())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.template_content, template_content)

    def test_get(self):

        template_content = self.create_template_content()

        response = self.client.get(reverse('publish_template_content', kwargs=self.get_url_kwargs()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['template_content'], template_content)
        self.assertTrue(response.context_data['publication'])
        self.assertTrue(len(response.context_data['publication_errors']) > 0)

        # create complete ltc
        post_data = self.get_post_data()
        post_kwargs = {
            'app_uid' : self.app.uid,
            'pk' : self.template_content.id,
        }
        post_url = reverse('manage_template_content', kwargs=post_kwargs)
        self.client.post(post_url, post_data)
        # create test_image and multi_image
        self.create_draft_image_microcontent(template_content, 'test_image', self.app.primary_language)
        self.create_draft_image_microcontent(template_content, 'multi_image', self.app.primary_language)

        for language in SecondaryAppLanguages.objects.filter(app=self.app):
            language.delete()

        response = self.client.get(reverse('publish_template_content', kwargs=self.get_url_kwargs()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['template_content'], template_content)
        self.assertTrue(response.context_data['publication'])
        self.assertEqual(response.context_data['publication_errors'], [])

        ltc = template_content.get_localized(self.app.primary_language)
        self.assertEqual(ltc.published_version, 1)


@test_settings
class TestUnpublishTemplateContent(ManageMicroContentsMixin, WithPublishedApp, CommonSetUp, WithUser, WithApp,
                                 WithOnlineContent, WithMedia, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
        }

        return url_kwargs
    
    def test_dispatch_no_ajax(self):
        template_content = self.create_template_content()
        view, request = self.get_view(UnpublishTemplateContent, 'unpublish_template_content')

        response = view.dispatch(request, **self.get_url_kwargs())
        self.assertEqual(response.status_code, 400)


    def test_dispatch(self):

        template_content = self.create_template_content()
        view, request = self.get_view(UnpublishTemplateContent, 'unpublish_template_content')
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        response = view.dispatch(request, **self.get_url_kwargs())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.template_content, template_content)


    def test_get_context_data(self):

        template_content = self.create_template_content()
        view, request = self.get_view(UnpublishTemplateContent, 'unpublish_template_content')
        view.template_content = template_content
        
        context = view.get_context_data(**{})
        self.assertEqual(context['template_content'], template_content)
        self.assertFalse(context['success'])

    def test_post(self):

        template_content = self.create_template_content()

        response = self.client.get(reverse('publish_template_content', kwargs=self.get_url_kwargs()))

        # create complete ltc
        post_data = self.get_post_data()
        post_kwargs = {
            'app_uid' : self.app.uid,
            'pk' : self.template_content.id,
        }
        post_url = reverse('manage_template_content', kwargs=post_kwargs)
        self.client.post(post_url, post_data)
        # create test_image and multi_image
        self.create_draft_image_microcontent(template_content, 'test_image', self.app.primary_language)
        self.create_draft_image_microcontent(template_content, 'multi_image', self.app.primary_language)

        for language in SecondaryAppLanguages.objects.filter(app=self.app):
            language.delete()

        ltc = template_content.get_localized(self.app.primary_language)

        response = self.client.get(reverse('publish_template_content', kwargs=self.get_url_kwargs()))

        ltc.refresh_from_db()
        self.assertEqual(ltc.published_version, 1)

        # test unpublish
        response = self.client.post(reverse('unpublish_template_content', kwargs=self.get_url_kwargs()), {},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])

        ltc.refresh_from_db()
        self.assertEqual(ltc.published_version, None)
        

@test_settings
class TestDeleteMicroContent(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
            'language' : self.app.primary_language,
        }

        return url_kwargs
    

    def test_dispatch(self):
        template_content = self.create_template_content()
        view, request = self.get_view(DeleteMicroContent, 'DeleteMicroContent')

        get_data = {
            'meta_pk' : 1,
            'localized_pk' : 2,
            'microcontentcategory' : 'microcontent',
            'microcontenttype' : 'test',
        }
        request.GET = get_data

        response = view.dispatch(request, **self.get_url_kwargs())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.language, self.app.primary_language)
        self.assertEqual(view.template_content, template_content)
        

    def test_get_context_data(self):

        template_content = self.create_template_content()
        view, request = self.get_view(DeleteMicroContent, 'DeleteMicroContent')

        view.template_content = template_content
        view.language = self.app.primary_language

        context = view.get_context_data(**{})
        self.assertEqual(context['template_content'], template_content)
        self.assertEqual(context['language'], self.app.primary_language)
        self.assertEqual(context['view_name'], view.__class__.__name__)


    def test_delete_microcontent_primary_language(self):

        template_content = self.create_template_content()
        microcontent_type = 'simple_content'
        #create microcontent
        lmc = self.create_draft_microcontent(template_content, microcontent_type, self.app.primary_language)
        microcontent = lmc.microcontent
        
        view, request = self.get_view(DeleteMicroContent, 'DeleteMicroContent')

        qry = DraftTextMicroContent.objects.filter(template_content=template_content,
                                                   microcontent_type=microcontent_type)

        self.assertTrue(qry.exists())

        view.delete_microcontent(microcontent, self.app.primary_language)

        self.assertFalse(qry.exists())


    def test_delete_microcontent_secondary_language(self):

        secondary_language = 'en'

        template_content = self.create_template_content()
        microcontent_type = 'simple_content'
        #create microcontent
        lmc = self.create_draft_microcontent(template_content, microcontent_type, self.app.primary_language)
        microcontent = lmc.microcontent

        secondary_lmc = self.create_localized_draft_microcontent(microcontent, secondary_language)
        
        view, request = self.get_view(DeleteMicroContent, 'DeleteMicroContent')

        qry = DraftTextMicroContent.objects.filter(template_content=template_content,
                                                   microcontent_type=microcontent_type)

        locale_qry = LocalizedDraftTextMicroContent.objects.filter(microcontent=microcontent,
                                                                             language=self.app.primary_language)
        secondary_locale_qry = LocalizedDraftTextMicroContent.objects.filter(microcontent=microcontent,
                                                                             language=secondary_language)

        self.assertTrue(qry.exists())
        self.assertTrue(locale_qry.exists())
        self.assertTrue(secondary_locale_qry.exists())

        view.delete_microcontent(microcontent, secondary_language)

        self.assertTrue(qry.exists())
        self.assertTrue(locale_qry.exists())
        self.assertFalse(secondary_locale_qry.exists())


    def test_get(self):

        template_content = self.create_template_content()

        url = reverse('DeleteMicroContent', kwargs=self.get_url_kwargs())
                      
        get_data = {
            'meta_pk' : 1,
            'localized_pk' : 2,
            'microcontentcategory' : 'microcontent',
            'microcontenttype' : 'test',
        }
                      
        response = self.client.get(url, get_data)

        self.assertEqual(response.context_data['template_content'], template_content)
        self.assertEqual(response.context_data['language'], self.app.primary_language)
        self.assertEqual(response.context_data['view_name'], 'DeleteMicroContent')

        form = response.context_data['form']
        self.assertEqual(form.initial['localized_pk'], str(get_data['localized_pk']))
        self.assertEqual(form.initial['microcontent_category'], get_data['microcontentcategory'])
        self.assertEqual(form.initial['microcontent_type'], get_data['microcontenttype'])


    def test_post_invalid(self):

        template_content = self.create_template_content()

        microcontent_type = 'simple_content'

        lmc = self.create_draft_microcontent(template_content, microcontent_type, self.app.primary_language)
        microcontent = lmc.microcontent

        post_data = {
            'meta_pk' : microcontent.pk,
            'microcontent_category' : 'microcontent',
            'microcontent_type' : microcontent.microcontent_type,
        }

        url = reverse('DeleteMicroContent', kwargs=self.get_url_kwargs())

        response = self.client.post(url, post_data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data['success'])

        qry = DraftTextMicroContent.objects.filter(template_content=template_content,
                                                   microcontent_type=microcontent_type)

        self.assertTrue(qry.exists())


    def test_post_valid(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)
        ltc.translation_ready = True
        ltc.save()

        microcontent_type = 'simple_content'

        lmc = self.create_draft_microcontent(template_content, microcontent_type, self.app.primary_language)
        microcontent = lmc.microcontent

        post_data = {
            'meta_pk' : microcontent.pk,
            'localized_pk' : lmc.pk,
            'microcontent_category' : 'microcontent',
            'microcontent_type' : microcontent.microcontent_type,
        }

        url = reverse('DeleteMicroContent', kwargs=self.get_url_kwargs())

        response = self.client.post(url, post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])

        qry = DraftTextMicroContent.objects.filter(template_content=template_content,
                                                   microcontent_type=microcontent_type)

        self.assertFalse(qry.exists())

        ltc.refresh_from_db()
        self.assertFalse(ltc.translation_ready)


@test_settings
class TestDeleteFileContent(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, WithMedia,
                            TestCase):

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
            'language' : self.app.primary_language,
        }

        return url_kwargs
    

    def test_on_success(self):

        template_content = self.create_template_content()
        
        microcontent_type = 'image'
        #create microcontent
        limc = self.create_draft_image_microcontent(template_content, microcontent_type, self.app.primary_language)
        microcontent = limc.microcontent
        
        view, request = self.get_view(DeleteFileContent, 'DeleteFileContent')

        post_data = {
            'meta_pk' : microcontent.pk,
            'localized_pk' : limc.pk,
            'microcontent_category' : 'image',
            'microcontent_type' : microcontent.microcontent_type,
        }
        
        form = view.form_class(data=post_data)

        form.is_valid()

        self.assertEqual(form.errors, {})

        context = {}
        response = view.on_success(context, form)

        self.assertEqual(response.context_data['microcontent_category'], 'image')
        self.assertEqual(response.context_data['microcontent_type'], microcontent_type)
        

@test_settings
class TestUploadFile(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, WithMedia,
                     WithImageForForm, TestCase):

    microcontent_type = 'image'
    microcontent_category = 'image'

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
            'microcontent_category' : self.microcontent_category,
            'microcontent_type' : self.microcontent_type,
            'language' : self.app.primary_language,
        }

        return url_kwargs


    def get_post_data(self):

        image = self.get_image('test_image.jpg')

        post_data = {
            'pk' : '',
            'template_content_id' : self.template_content.id,
            'language' : self.app.primary_language,
            'file' : image,
        }

        return post_data
        

    def test_post_invalid(self):

        template_content = self.create_template_content()

        limc = self.create_draft_image_microcontent(template_content, self.microcontent_type,
                                                    self.app.primary_language)

        url = reverse('upload_image', kwargs=self.get_url_kwargs())

        post_data = self.get_post_data()
        del post_data['file']
        
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['template_content'], template_content)
        self.assertEqual(response.context_data['language'], self.app.primary_language)
        self.assertEqual(response.context_data['form'].__class__, UploadImage.form_class)
        self.assertFalse(response.context_data['form'].is_valid())
        

    def test_post_valid(self):

        template_content = self.create_template_content()

        limc = self.create_draft_image_microcontent(template_content, self.microcontent_type,
                                                    self.app.primary_language)

        url = reverse('upload_image', kwargs=self.get_url_kwargs())

        post_data = self.get_post_data()
        
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['template_content'], template_content)
        self.assertEqual(response.context_data['language'], self.app.primary_language)
        self.assertEqual(response.context_data['form'].__class__, UploadImage.form_class)
        self.assertTrue(response.context_data['form'].is_valid())

        qry = DraftImageMicroContent.objects.filter(template_content=template_content)
        self.assertTrue(qry.exists())

        microcontent = qry.first()
        locale_qry = LocalizedDraftImageMicroContent.objects.filter(microcontent=microcontent)

        self.assertTrue(locale_qry.exists())

        
@test_settings
class TestManageImageUpload(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, WithMedia,
                     WithImageForForm, TestCase):

    microcontent_category = 'image'
    microcontent_type = 'image'

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
            'microcontent_category' : self.microcontent_category,
            'language' : self.app.primary_language,
        }

        if self.microcontent:
            url_kwargs['microcontent_id'] = self.microcontent.id
        else:
            url_kwargs['microcontent_type'] = self.microcontent_type

        return url_kwargs


    def get_post_data(self):

        post_data = {
            'creator_name' : 'image creator',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'template_content_id' : self.template_content.id,
            'source_image' : self.get_image('test_image.jpg'),
            'image_type' : self.microcontent_type,
        }

        return post_data
    

    def test_dispatch(self):

        template_content = self.create_template_content()
        self.microcontent = None
        
        view, request = self.get_view(ManageImageUpload, 'upload_licenced_image')
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        response = view.dispatch(request, **self.get_url_kwargs())
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.language, self.app.primary_language)
        self.assertEqual(view.template_content, template_content)
        self.assertEqual(view.microcontent_category, self.microcontent_category)
        self.assertEqual(view.localized_instance, None)
        self.assertEqual(view.meta_instance, None)
        self.assertEqual(view.MetaModel, DraftImageMicroContent)
        self.assertEqual(view.LocaleModel, LocalizedDraftImageMicroContent)
        

   
    def test_dispatch_with_microcontent_id(self):

        template_content = self.create_template_content()

        limc = self.create_draft_image_microcontent(template_content, self.microcontent_type,
                                                    self.app.primary_language)
        self.microcontent = limc.microcontent
        
        view, request = self.get_view(ManageImageUpload, 'update_licenced_image')
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        url_kwargs = self.get_url_kwargs()
        
        response = view.dispatch(request, **url_kwargs)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.language, self.app.primary_language)
        self.assertEqual(view.template_content, template_content)
        self.assertEqual(view.microcontent_category, self.microcontent_category)
        self.assertEqual(view.localized_instance, limc)
        self.assertEqual(view.meta_instance, self.microcontent)
        self.assertEqual(view.MetaModel, DraftImageMicroContent)
        self.assertEqual(view.LocaleModel, LocalizedDraftImageMicroContent)
    
    def test_get_context_data(self):

        template_content = self.create_template_content()
        self.microcontent = None
        
        view, request = self.get_view(ManageImageUpload, 'upload_licenced_image')
        view.template_content = template_content
        view.microcontent_category = self.microcontent_category
        view.microcontent_type = self.microcontent_type
        view.meta_instance = None
        view.localized_instance = None
        view.language = self.app.primary_language
        
        context = view.get_context_data(**{})
        
        self.assertEqual(context['language'], self.app.primary_language)
        self.assertEqual(context['template_content'], template_content)
        self.assertEqual(context['microcontent_category'], self.microcontent_category)
        self.assertEqual(context['microcontent_type'], self.microcontent_type)
        self.assertEqual(context['localized_instance'], None)
        self.assertEqual(context['meta_instance'], None)
        

    def test_get_initial(self):

        template_content = self.create_template_content()

        limc = self.create_draft_image_microcontent(template_content, self.microcontent_type,
                                                    self.app.primary_language)
        self.microcontent = limc.microcontent
        
        view, request = self.get_view(ManageImageUpload, 'update_licenced_image')
        view.localized_instance = limc
        view.licence_registry_entry = None

        initial = view.get_initial()

        self.assertEqual(initial['source_image'], limc.content)


    def test_get_form_kwargs(self):

        template_content = self.create_template_content()

        limc = self.create_draft_image_microcontent(template_content, self.microcontent_type,
                                                    self.app.primary_language)
        self.microcontent = limc.microcontent
        
        view, request = self.get_view(ManageImageUpload, 'update_licenced_image')
        view.localized_instance = limc
        view.licence_registry_entry = None

        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['current_image'], limc.content)


    def test_form_valid(self):

        template_content = self.create_template_content()
        
        self.microcontent = None
        
        url = reverse('upload_licenced_image', kwargs=self.get_url_kwargs())

        post_data = self.get_post_data()
        
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        form = response.context_data['form']
        self.assertEqual(form.errors, {})

        qry = DraftImageMicroContent.objects.filter(template_content=template_content,
                                                    microcontent_type=self.microcontent_type)
        self.assertTrue(qry.exists())

        microcontent = qry.first()
        locale_qry = LocalizedDraftImageMicroContent.objects.filter(microcontent=microcontent)

        self.assertTrue(locale_qry.exists())

    def test_form_valid_update(self):

        template_content = self.create_template_content()

        limc = self.create_draft_image_microcontent(template_content, self.microcontent_type,
                                                    self.app.primary_language)
        
        self.microcontent = limc.microcontent
        
        url = reverse('update_licenced_image', kwargs=self.get_url_kwargs())

        post_data = self.get_post_data()
        
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        form = response.context_data['form']
        self.assertEqual(form.errors, {})

        qry = DraftImageMicroContent.objects.filter(template_content=template_content,
                                                    microcontent_type=self.microcontent_type)

        self.assertEqual(len(qry), 1)
        self.assertEqual(qry.first(), self.microcontent)

        locale_qry = LocalizedDraftImageMicroContent.objects.filter(microcontent=self.microcontent)

        self.assertTrue(locale_qry.exists())


@test_settings
class TestGetFormField(WithPublishedApp, CommonSetUp, WithUser, WithApp, WithOnlineContent, WithMedia,
                     WithImageForForm, TestCase):

    microcontent_category = 'image'
    microcontent_type = 'test_image'

    def get_url_kwargs(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
            'template_content_id' : self.template_content.id,
            'microcontent_category' : self.microcontent_category,
            'microcontent_type' : self.microcontent_type,
            'language' : self.app.primary_language
        }

        return url_kwargs
    
        
    def test_dispatch(self):

        template_content = self.create_template_content()

        view, request = self.get_view(GetFormField, 'get_form_field')
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        response = view.dispatch(request, **self.get_url_kwargs())
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.language, self.app.primary_language)
        self.assertEqual(view.template_content, template_content)
        self.assertEqual(view.microcontent_category, self.microcontent_category)
        self.assertEqual(view.microcontent_type, self.microcontent_type)
        

    def test_get_context_data(self):

        template_content = self.create_template_content()

        view, request = self.get_view(GetFormField, 'get_form_field')
        view.language = self.app.primary_language
        view.template_content = template_content
        view.microcontent_category = self.microcontent_category
        view.microcontent_type = self.microcontent_type

        context = view.get_context_data(**{})
        self.assertEqual(context['language'], self.app.primary_language)
        self.assertEqual(context['template_content'], template_content)

    def test_get_form(self):

        template_content = self.create_template_content()

        view, request = self.get_view(GetFormField, 'get_form_field')
        view.language = self.app.primary_language
        view.template_content = template_content
        view.microcontent_type = self.microcontent_type
        view.microcontent_category = self.microcontent_category

        form = view.get_form()

        self.assertTrue('test_image' in form.fields)
