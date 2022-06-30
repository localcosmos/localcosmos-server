###################################################################################################################
#
# TESTS FOR MODELS
# - this file only covers settings.LOCALCOSMOS_PRIVATE == True
#
###################################################################################################################
from django.conf import settings
from django.test import TestCase
from django.template.defaultfilters import slugify
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

from django.utils import timezone

from localcosmos_server.models import SecondaryAppLanguages

from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia

from localcosmos_server.tests.common import test_settings, TEST_IMAGE_PATH


from localcosmos_server.online_content.models import (TEMPLATE_TYPES, TemplateContent, LocalizedTemplateContent,
            DraftTextMicroContent, LocalizedDraftTextMicroContent, TemplateContentFlags, SlugTrail, FlagTree,
            PublishedTextMicroContent, LocalizedPublishedTextMicroContent, DraftImageMicroContent,
            LocalizedDraftImageMicroContent, PublishedImageMicroContent, LocalizedPublishedImageMicroContent)

from localcosmos_server.online_content.fields import MultiContentField
from localcosmos_server.online_content.widgets import MultiContentWidget

import os

from random import choice
from string import ascii_uppercase

# this is just a copy/paste from the config.json file
TEST_OC_SETTINGS = {
    "verbose_template_names" : {
            "page/free_page.html" : {
                    "de" : "Freie Seite",
                    "en" : "Free Page"
            },
            "page/test.html" : {
                    "de" : "Test Seite",
                    "en" : "Test Page"
            },
            "feature/news.html" : {
                    "de" : "News Eintrag",
                    "en" : "News entry"
            }
    },
    "max_flag_levels" : 2,
    "flags" : {
            "main_navigation" : {
                    "template_name" : "flag/main_navigation.html",
                    "name" : "Main Navigation"
            }
    }
}

class WithTemplateContent:

    title = 'Test Title'
    navigation_link_name = 'Test Nav name'

    template_name = 'page/free_page.html'
    simple_template_name = 'page/free_page.html'
    template_type = 'page'

    def create_template_content(self):

        self.user = self.create_user()

        # type 'page'
        template_type = TEMPLATE_TYPES[0][0]

        template_content = TemplateContent.objects.create(self.user, self.app, self.app.primary_language, self.title,
                                        self.navigation_link_name, self.simple_template_name, template_type)

        return template_content


    def create_freepage_microcontent(self, template_content, language):

        draft_content, created = DraftTextMicroContent.objects.get_or_create(
            template_content=template_content,
            microcontent_type = 'freepage_content',
        )


        ldtmc = LocalizedDraftTextMicroContent(
            microcontent = draft_content,
            content = 'some text content',
            language = language,
            creator = self.user,
        )

        ldtmc.save()

        return draft_content, ldtmc
    

@test_settings
class TestTemplateContent(WithUser, WithApp, WithTemplateContent, TestCase):

    # only published apps can access template content settings on lc private
    def setUp(self):
        super().setUp()
        published_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.testapp_relative_www_path)

        self.app.published_version_path = published_version_path

        self.app.save()
        

    def test_create(self):

        user = self.create_user()

        for choice in TEMPLATE_TYPES:

            template_type = choice[0]

            template_content = TemplateContent.objects.create(user, self.app, self.app.primary_language,
                self.title, self.navigation_link_name, self.template_name, template_type)

            self.assertEqual(template_content.app, self.app)
            self.assertEqual(template_content.template_name, self.template_name)
            self.assertEqual(template_content.template_type, template_type)

            ltc_exists = LocalizedTemplateContent.objects.filter(template_content=template_content,
                                                       language=self.app.primary_language).exists()

            self.assertTrue(ltc_exists)
            # ltc is tested separately
            

    def test_get_online_content_settings(self):

        template_content = self.create_template_content()
        
        oc_settings = template_content.get_online_content_settings()

        self.assertTrue('flags' in oc_settings)
        self.assertTrue('verbose_template_names' in oc_settings)


    def test_get_verbose_template_name(self):

        template_content = self.create_template_content()
        verbose_names = TEST_OC_SETTINGS['verbose_template_names'][template_content.template_name]
        
        verbose_name = template_content.verbose_template_name()
        expected_name = verbose_names[self.app.primary_language]
        self.assertEqual(verbose_name, expected_name)

        # test en
        verbose_name_en = template_content.verbose_template_name(language_code='en')
        expected_name_en = verbose_names['en']
        self.assertEqual(verbose_name_en, expected_name_en)

        # test non-existant fr
        verbose_name_fr = template_content.verbose_template_name(language_code='fr')
        expected_name_fr = 'Free page'#template_content.template_name
        self.assertEqual(verbose_name_fr, expected_name_fr)
        

    def test_get_localized(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)
        self.assertEqual(ltc.language, self.app.primary_language)

        ltc = template_content.get_localized('fr')
        self.assertEqual(ltc, None)
        

    def test_locales(self):

        template_content = self.create_template_content()
        ltc = LocalizedTemplateContent.objects.create(self.user, template_content, 'en', self.title,
                                                      self.navigation_link_name)
    
        locales = template_content.locales()
        self.assertEqual(locales.count(), 2)


    def test_template_path(self):

        template_content = self.create_template_content()

        template_path = template_content.template_path(self.app)

        self.assertTrue(template_path.endswith(template_content.template_name))

    # tested by localcosmos_server.TestApp
    def test_get_template(self):
        template_content = self.create_template_content()
        template_content.get_template()


    def test_primary_title(self):
        template_content = self.create_template_content()

        title = template_content.primary_title()
        self.assertEqual(title, self.title)

        # test none
        self.app.primary_language = 'jp'
        self.app.save()

        title = template_content.primary_title()
        self.assertEqual(title, None)
        

    def test_validate(self):
        template_content = self.create_template_content()

        result = template_content.validate(self.app)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])


    def test_translation_complete(self):

        # test incomplete primary language
        template_content = self.create_template_content()

        errors = template_content.translation_complete(self.app.primary_language)

        # 2 errors: translatin is not ready, ltc is incomplete
        self.assertEqual(len(errors), 2)
        self.assertIn('still working', str(errors[0]))
        # ltc component is not complete
        self.assertIn('required but still missing', str(errors[1]))


        errors_2 = template_content.translation_complete('fr')
        self.assertEqual(len(errors_2), 1)
        self.assertIn('is missing', str(errors_2[0]))

        # complete, but not translation_ready
        draft_content, ltdmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        errors_3 = template_content.translation_complete(self.app.primary_language)
        self.assertEqual(len(errors_3), 1)
        self.assertIn('still working', str(errors_3[0]))

        # complete and translation_ready = True
        ltc = template_content.get_localized(self.app.primary_language)
        ltc.translation_ready=True
        ltc.save()

        errors_4 = template_content.translation_complete(self.app.primary_language)
        self.assertEqual(errors_4, [])
        

    def test_publish_no_secondary_languages(self):

        template_content = self.create_template_content()

        secondary_languages = SecondaryAppLanguages.objects.filter(app=self.app)
        for language in secondary_languages:
            language.delete()

        # check errors : unready
        errors = template_content.publish()
        self.assertEqual(len(errors), 1)

        ltc = template_content.get_localized(self.app.primary_language)
        self.assertEqual(ltc.published_version, None)
        self.assertEqual(ltc.published_at, None)
        
         
        draft_content, ldtmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        # everything is ready for publication now
        # translation_ready is not needed if there are no secondary languages
        errors_2 = template_content.publish()
        self.assertEqual(errors_2, [])

        ltc.refresh_from_db()
        self.assertEqual(ltc.published_version, 1)
        self.assertEqual(ltc.draft_version, 1)
        self.assertTrue(ltc.published_at != None)
         

    def test_publish_with_secondary_languages(self):

        template_content = self.create_template_content()

        errors = template_content.publish()
        self.assertEqual(len(errors), 3)

        # primary language: missing component
        self.assertIn('is still working', errors[0])
        self.assertIn('required but still missing', errors[1])
        self.assertIn('Translation for the language', errors[2])

        # create microcontent
        draft_content, ldtmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        errors_2 = template_content.publish()
        self.assertEqual(len(errors_2), 2)
        self.assertIn('is still working', errors_2[0])
        self.assertIn('Translation for the language', errors_2[1])

        # set translation ready
        ltc = template_content.get_localized(self.app.primary_language)
        ltc.translation_ready=True
        ltc.save()

        errors_3 = template_content.publish()
        self.assertEqual(len(errors_3), 1)
        self.assertIn('Translation for the language', errors_3[0])

        # create ltc for secondary languages
        # translator is still working
        for language in self.app.secondary_languages():
            ltc = LocalizedTemplateContent.objects.create(self.user, template_content, language,
                                                    'Titel {}'.format(language), 'Link name {}'.format(language))

            ltc.save()

        errors_4 = template_content.publish()
        self.assertEqual(len(errors_4), 2)
        self.assertIn('is still working', errors_4[0])
        self.assertIn('is missing for the language', errors_4[1])
        

        for language in self.app.secondary_languages():
            draft_content, ldtmc = self.create_freepage_microcontent(template_content, language)


        errors_5 = template_content.publish()
        self.assertEqual(len(errors_5), 1)
        self.assertIn('is still working', errors_5[0])

        for language in self.app.secondary_languages():
            ltc = template_content.get_localized(language)
            ltc.translation_ready = True
            ltc.save()


        errors_6 = template_content.publish()
        self.assertEqual([], errors_6)

        for language in self.app.languages():
            ltc = template_content.get_localized(language)
            self.assertEqual(ltc.published_version, 1)
            self.assertTrue(ltc.published_at != None)
            self.assertEqual(ltc.draft_version, 1)

        
    def test_set_translated_localized_template_content_version(self):
        # case: seoncdary language is added pimary language already is version 2

        template_content = self.create_template_content()

        secondary_languages = SecondaryAppLanguages.objects.filter(app=self.app)
        for language in secondary_languages:
            language.delete()


        draft_content, ldtmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        errors = template_content.publish()
        
        ltc = template_content.get_localized(self.app.primary_language)
        self.assertEqual(ltc.published_version, 1)
        self.assertEqual(ltc.draft_version, 1)

        ltc.save()

        ltc.refresh_from_db()
        self.assertEqual(ltc.draft_version, 2)


        secondary_language = SecondaryAppLanguages(
            app=self.app,
            language_code='en'
        )

        secondary_language.save()

        language_code = secondary_language.language_code
        secondary_ltc = LocalizedTemplateContent.objects.create(self.user, template_content, language_code,
                                        'Titel {}'.format(language_code), 'Link name {}'.format(language_code))

        secondary_ltc.save()

        self.assertEqual(secondary_ltc.draft_version, 2)
         

    def test_flags(self):
        template_content = self.create_template_content()

        flag_name = 'test_flag'

        flag = TemplateContentFlags(
            template_content=template_content,
            flag=flag_name,
        )

        flag.save()

        flags = template_content.flags()

        self.assertEqual(flags,[flag_name])


    def test_unpublish(self):

        template_content = self.create_template_content()

        draft_content, ldtmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        primary_ltc = template_content.get_localized(self.app.primary_language)
        primary_ltc.translation_ready = True
        primary_ltc.save()
       
        for language in self.app.secondary_languages():
            ltc = LocalizedTemplateContent.objects.create(self.user, template_content, language,
                    'Titel {}'.format(language), 'Link name {}'.format(language))
            draft_content, ldtmc = self.create_freepage_microcontent(template_content, language)

            ltc.translation_ready = True
            ltc.save()

        errors = template_content.publish()

        for language in self.app.languages():
            ltc = template_content.get_localized(language)
            self.assertEqual(ltc.published_version, 1)

        template_content.unpublish()

        for language in self.app.languages():
            ltc = template_content.get_localized(language)
            self.assertEqual(ltc.published_version, None)
            self.assertEqual(ltc.published_at, None)
        

    def test_is_published(self):

        template_content = self.create_template_content()

        draft_content, ldtmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        primary_ltc = template_content.get_localized(self.app.primary_language)
        primary_ltc.translation_ready = True
        primary_ltc.save()
       
        for language in self.app.secondary_languages():
            ltc = LocalizedTemplateContent.objects.create(self.user, template_content, language,
                    'Titel {}'.format(language), 'Link name {}'.format(language))
            draft_content, ldtmc = self.create_freepage_microcontent(template_content, language)

            ltc.translation_ready = True
            ltc.save()

        self.assertFalse(template_content.is_published)
        
        errors = template_content.publish()
        self.assertTrue(template_content.is_published)


    def test_str(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        self.assertEqual(str(template_content), ltc.draft_title)

        ltc.delete()

        self.assertEqual(str(template_content), 'Template Content %s' % template_content.pk)
        


@test_settings
class TestLocalizedTemplateContent(WithUser, WithApp, WithTemplateContent, TestCase):

    # only published apps can access template content settings on lc private
    def setUp(self):
        super().setUp()
        published_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.testapp_relative_www_path)

        self.app.published_version_path = published_version_path

        self.app.save()
        

    def test_create(self):

        user = self.create_user()

        template_content = TemplateContent(
            app = self.app,
            template_name = self.template_name,
            template_type = self.template_type,
        )
        template_content.save()

        ltc = LocalizedTemplateContent.objects.create(user, template_content, self.app.primary_language,
                                                      self.title, self.navigation_link_name)

        ltc = LocalizedTemplateContent.objects.get(pk=ltc.pk)
        self.assertEqual(ltc.draft_title, self.title)
        self.assertEqual(ltc.draft_navigation_link_name, self.navigation_link_name)
        self.assertEqual(ltc.language, self.app.primary_language)
        self.assertEqual(ltc.template_content, template_content)
        self.assertEqual(ltc.creator, user)
        

    def test_generate_slug_base(self):

        title_1 = 'TestTitle'
        slug_base = LocalizedTemplateContent.objects.generate_slug_base(title_1)

        self.assertEqual(len(slug_base), len(title_1))

        title_2 = ''.join(choice(ascii_uppercase) for i in range(200))

        slug_base_2 = LocalizedTemplateContent.objects.generate_slug_base(title_2)
        self.assertEqual(len(slug_base_2), 99)
        

    def test_generate_slug(self):

        slug_1 = LocalizedTemplateContent.objects.generate_slug(self.title)
        self.assertEqual(slug_1, slugify(self.title))

        template_content = self.create_template_content()

        slug_2 = LocalizedTemplateContent.objects.generate_slug(self.title)
        expected_slug = '{0}-2'.format(slugify(self.title))
        self.assertEqual(slug_2, expected_slug)


    def test_translation_complete(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        errors = ltc.translation_complete()

        self.assertEqual(len(errors), 1)
        self.assertIn('is required but still missing', errors[0])

        draft_content, ldtmc = self.create_freepage_microcontent(template_content, self.app.primary_language)

        errors_2 = ltc.translation_complete()

        self.assertEqual(errors_2, [])

        ltc_en = ltc = LocalizedTemplateContent.objects.create(self.user, template_content, 'en', self.title,
                                                               self.navigation_link_name)
        
        errors_3 = ltc_en.translation_complete()
        self.assertEqual(len(errors_3), 1)
        self.assertIn('is missing for the language', errors_3[0])


    def test_flags(self):

        template_content = self.create_template_content()

        flag_name = 'test_flag'

        flag = TemplateContentFlags(
            template_content=template_content,
            flag=flag_name,
        )

        flag.save()

        ltc = template_content.get_localized(self.app.primary_language)

        flags = ltc.flags()

        self.assertEqual(flags,[flag_name])


    def test_update_preview_token(self):

        # this saves the ltc -> no version adjustment
        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        draft_version = ltc.draft_version
        published_version = ltc.published_version

        now = timezone.now()
        ltc.update_preview_token()

        self.assertEqual(ltc.draft_version, draft_version)
        self.assertEqual(ltc.published_version, published_version)

        delta = ltc.preview_token_created_at - now
        self.assertTrue(delta.seconds < 1)
        self.assertTrue(ltc.preview_token != None)
        

    def test_validate_preview_token(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        token = 'test'
        is_valid = ltc.validate_preview_token(token)
        self.assertFalse(is_valid)
        
        ltc.update_preview_token()
        is_valid_2 = ltc.validate_preview_token(token)
        self.assertFalse(is_valid_2)

        is_valid_3 = ltc.validate_preview_token(ltc.preview_token)
        self.assertTrue(is_valid_3)

        is_valid_4 = ltc.validate_preview_token(ltc.preview_token, maxage_minutes = -1)
        self.assertFalse(is_valid_4)


    def test_get_template(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)
        template = ltc.get_template()
        self.assertTrue(template != None)
        

    def test_in_app_link(self):

        template_content = self.create_template_content()
        ltc = template_content.get_localized(self.app.primary_language)
        ltc.update_preview_token()

        in_app_link = ltc.in_app_link()
        self.assertEqual(in_app_link, '/online-content/{0}/'.format(ltc.slug))

        in_app_link = ltc.in_app_link(app_state='preview')
        self.assertEqual(in_app_link, '/online-content/{0}/{1}/'.format(ltc.slug, ltc.preview_token))


    def test_publish(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        self.assertEqual(ltc.published_at, None)
        self.assertEqual(ltc.navigation_link_name, None)
        self.assertEqual(ltc.published_title, None)
        self.assertEqual(ltc.published_version, None)
        
        ltc.publish()

        self.assertEqual(ltc.draft_navigation_link_name, ltc.navigation_link_name)
        self.assertEqual(ltc.draft_title, ltc.published_title)
        self.assertEqual(ltc.draft_version, ltc.published_version)
        self.assertTrue(ltc.published_at != None)


    def test_save(self):

        template_content = self.create_template_content()

        ltc = template_content.get_localized(self.app.primary_language)

        old_slug = ltc.slug

        ltc.save()
        self.assertEqual(old_slug, ltc.slug)
        
        # check: new slug
        new_title = 'Completely different'
        ltc.draft_title = new_title

        ltc.save()

        self.assertFalse(old_slug == ltc.slug)
        slug_trail = SlugTrail.objects.get(old_slug=old_slug)
        self.assertEqual(slug_trail.new_slug, ltc.slug)

        ltc.publish()

        # check: unready translation, increment version
        ltc.translation_ready = True
        ltc.save(disallow_new_version=True)
        self.assertTrue(ltc.draft_version == 1)
        self.assertTrue(ltc.translation_ready)

        ltc.save()
        self.assertTrue(ltc.draft_version == 2)
        self.assertFalse(ltc.translation_ready)

        # check: no pk, master ltc.version > 1
        # covered by: TestTemplateContent.test_set_translated_localized_template_content_version



class WithFlags:

    flag_names = ['nav', 'footer']

    def create_flags(self, template_content):

        
        for flag_name in self.flag_names:
            flag = TemplateContentFlags(
                template_content = template_content,
                flag = flag_name,
            )
            flag.save()
    
@test_settings
class TestFlagTree(WithUser, WithApp, WithTemplateContent, WithFlags, TestCase):        

    def test_init(self):

        template_content = self.create_template_content()

        self.create_flags(template_content)

        flags = TemplateContentFlags.objects.filter(flag=self.flag_names[0])
        flag_tree = FlagTree(flags, self.app.primary_language)

        self.assertEqual(set(flag_tree.flags.values_list('flag', flat=True)), set(flags.values_list('flag', flat=True)))
        self.assertEqual(flag_tree.language, self.app.primary_language)
        self.assertEqual(flag_tree.app_state, 'published')
        self.assertEqual(flag_tree.toplevel_count, 0)

        # set preview to True to generate 1 flag
        ltc = template_content.get_localized(self.app.primary_language)
        flag_tree = FlagTree(flags, self.app.primary_language, app_state='preview')
        self.assertEqual(flag_tree.app_state, 'preview')
        self.assertEqual(flag_tree.toplevel_count, 1)
        self.assertIn(ltc.draft_title, flag_tree.flag_tree)

        # published flag tree
        ltc.publish()
        flag_tree = FlagTree(flags, self.app.primary_language)
        self.assertEqual(flag_tree.app_state, 'published')
        self.assertEqual(flag_tree.toplevel_count, 1)
        self.assertIn(ltc.published_title, flag_tree.flag_tree)
        


    def test_get_tree_entry(self):

        template_content = self.create_template_content()

        self.create_flags(template_content)

        flags = TemplateContentFlags.objects.filter(flag=self.flag_names[0])
        flag_tree = FlagTree(flags, self.app.primary_language)

        tree_entry = flag_tree.get_tree_entry(flags.first())
        self.assertEqual(tree_entry, None)

        # preview
        ltc = template_content.get_localized(self.app.primary_language)
        flag_tree = FlagTree(flags, self.app.primary_language, app_state='preview')
        tree_entry = flag_tree.get_tree_entry(flags.first())
        self.assertEqual(tree_entry['children'], [])
        self.assertEqual(tree_entry['localized_template_content'], ltc)
        self.assertEqual(tree_entry['navigation_link_name'], ltc.draft_navigation_link_name)
        self.assertIn('in_app_link', tree_entry)

        ltc.publish()
        flag_tree = FlagTree(flags, self.app.primary_language)
        tree_entry = flag_tree.get_tree_entry(flags.first())
        self.assertEqual(tree_entry['children'], [])
        self.assertEqual(tree_entry['localized_template_content'], ltc)
        self.assertEqual(tree_entry['navigation_link_name'], ltc.navigation_link_name)
        self.assertIn('in_app_link', tree_entry)


    def test_iter(self):

        template_content = self.create_template_content()
        
        ltc = template_content.get_localized(self.app.primary_language)
        ltc.publish()

        self.create_flags(template_content)

        flags = TemplateContentFlags.objects.filter(flag=self.flag_names[0])
        flag_tree = FlagTree(flags, self.app.primary_language)

        expected_tree_entry = flag_tree.get_tree_entry(flags.first())

        for tree_entry in flag_tree:
            self.assertEqual(tree_entry, expected_tree_entry)


    def test_bool(self):

        template_content = self.create_template_content()

        self.create_flags(template_content)

        flags = TemplateContentFlags.objects.filter(flag=self.flag_names[0])
        flag_tree = FlagTree(flags, self.app.primary_language)
        
        self.assertFalse(bool(flag_tree))


        flag_tree = FlagTree(flags, self.app.primary_language, app_state='preview')
        self.assertTrue(bool(flag_tree))


        ltc = template_content.get_localized(self.app.primary_language)
        ltc.publish()

        flag_tree = FlagTree(flags, self.app.primary_language)
        self.assertTrue(bool(flag_tree))


@test_settings
class TestTemplateContentFlagsManager(WithUser, WithApp, WithTemplateContent, WithFlags, TestCase):


    # only published apps can access template content settings on lc private
    def setUp(self):
        super().setUp()
        published_version_path = os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.testapp_relative_www_path)

        self.app.published_version_path = published_version_path

        self.app.save()
        

    def test_get_tree(self):

        template_content = self.create_template_content()

        self.create_flags(template_content)
        
        flag_tree = TemplateContentFlags.objects.get_tree(self.app, self.flag_names[0], self.app.primary_language)

        self.assertEqual(flag_tree.language, self.app.primary_language)
        self.assertEqual(flag_tree.app_state, 'published')
        self.assertEqual(flag_tree.toplevel_count, 0)


        flag_tree = TemplateContentFlags.objects.get_tree(self.app, self.flag_names[0], self.app.primary_language,
                                                          app_state='preview')

        self.assertEqual(flag_tree.language, self.app.primary_language)
        self.assertEqual(flag_tree.app_state, 'preview')
        self.assertEqual(flag_tree.toplevel_count, 1)


        ltc = template_content.get_localized(self.app.primary_language)
        ltc.publish()
        flag_tree = TemplateContentFlags.objects.get_tree(self.app, self.flag_names[0], self.app.primary_language)
        self.assertEqual(flag_tree.language, self.app.primary_language)
        self.assertEqual(flag_tree.app_state, 'published')
        self.assertEqual(flag_tree.toplevel_count, 1)


# nothing to test currently
@test_settings
class TestTemplatecontentFlags(TestCase):

    def test(self):
        pass


class WithDraftTextMicroContent:

    microcontent_type = 'freepage_content'

    content = 'Freedom from the heart'

    def create_draft_text_mc(self, template_content):

        draft_text_mc = DraftTextMicroContent.objects.create(template_content, self.app.primary_language,
                                                             self.microcontent_type, self.content, self.user)

        return draft_text_mc
    

@test_settings
class TestDraftTextMicroContent(WithUser, WithApp, WithTemplateContent, WithDraftTextMicroContent, TestCase):
    

    def test_create(self):

        template_content = self.create_template_content()

        draft_text_mc = self.create_draft_text_mc(template_content)

        draft_text_mc.refresh_from_db()
        self.assertEqual(draft_text_mc.template_content, template_content)
        self.assertEqual(draft_text_mc.microcontent_type, self.microcontent_type)
        
        # local creation
        ldtmc = LocalizedDraftTextMicroContent.objects.get(microcontent=draft_text_mc)
        self.assertEqual(ldtmc.content, self.content)
        self.assertEqual(ldtmc.language, self.app.primary_language)
        self.assertEqual(ldtmc.creator, self.user)
        self.assertEqual(ldtmc.microcontent, draft_text_mc)

        
    def test_get_language_dependant(self):

        template_content = self.create_template_content()

        draft_text_mc = self.create_draft_text_mc(template_content)

        contents = DraftTextMicroContent.objects.get_language_dependant(template_content, self.microcontent_type,
                                                        self.app.primary_language)

        ldtmc = LocalizedDraftTextMicroContent.objects.get(microcontent=draft_text_mc)

        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0], ldtmc)
        

    def test_get_locale_model(self):

        LocaleModel = DraftTextMicroContent.get_locale_model()
        self.assertEqual(LocaleModel, LocalizedDraftTextMicroContent)


    def test_get_publication_model(self):

        PublicationModel = DraftTextMicroContent.get_publication_model()
        self.assertEqual(PublicationModel, PublishedTextMicroContent)
        

    def test_get_content(self):

        template_content = self.create_template_content()

        draft_text_mc = self.create_draft_text_mc(template_content)

        content = draft_text_mc.get_content(self.app.primary_language)
        self.assertEqual(content, self.content)

        content_2 = draft_text_mc.get_content('en')
        self.assertEqual(content_2, None)


    def test_get_localized(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        ldtmc = draft_text_mc.get_localized(self.app.primary_language)

        expected_ldtmc = LocalizedDraftTextMicroContent.objects.get(microcontent=draft_text_mc,
                                                                    language=self.app.primary_language)
        
        self.assertEqual(ldtmc, expected_ldtmc)

        non_existant_ldtmc = draft_text_mc.get_localized('fr')
        self.assertEqual(non_existant_ldtmc, None)
        

    def test_get_form_field(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        form_field = draft_text_mc.get_form_field(self.app, template_content, {})

        self.assertTrue(isinstance(form_field.widget, forms.Textarea))
        self.assertTrue(isinstance(form_field, forms.CharField))

        form_field = draft_text_mc.get_form_field(self.app, template_content, {}, 'short')

        self.assertTrue(isinstance(form_field.widget, forms.TextInput))
        self.assertTrue(isinstance(form_field, forms.CharField))

        form_field = draft_text_mc.get_form_field(self.app, template_content, {'multi':True})

        self.assertTrue(isinstance(form_field.widget, MultiContentWidget))
        self.assertTrue(isinstance(form_field, MultiContentField))
        

    def test_translation_complete(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        errors = draft_text_mc.translation_complete(self.app.primary_language)
        self.assertEqual(errors, [])

        errors_2 = draft_text_mc.translation_complete('en')
        self.assertEqual(len(errors_2), 1)
        self.assertIn('is missing for the language', errors_2[0])
    

    def test_set_content(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        content_2 = 'Edited content'
        draft_text_mc.set_content(content_2, self.user, self.app.primary_language)

        ldtmc = draft_text_mc.get_localized(self.app.primary_language)
        self.assertEqual(ldtmc.content, content_2)

        en_content = 'Translated content'
        draft_text_mc.set_content(en_content, self.user, 'en')

        ldtmc_en = draft_text_mc.get_localized('en')
        self.assertEqual(ldtmc_en.content, en_content)
    

    def test_publish(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        en_content = 'Translated content'
        draft_text_mc.set_content(en_content, self.user, 'en')

        draft_text_mc.publish(['de', 'en'])

        published_text_mc = PublishedTextMicroContent.objects.get(template_content=template_content,
                    microcontent_type=draft_text_mc.microcontent_type)

        ldtmc = draft_text_mc.get_localized(self.app.primary_language)
        lptmc = published_text_mc.get_localized(self.app.primary_language)

        self.assertEqual(ldtmc.content, lptmc.content)


        ldtmc_en = draft_text_mc.get_localized('en')
        lptmc_en = published_text_mc.get_localized('en')
        
        self.assertEqual(ldtmc_en.content, lptmc_en.content)


@test_settings
class TestLocalizedDraftTextMicroContent(WithUser, WithApp, WithTemplateContent, WithDraftTextMicroContent,
                                         TestCase):

    def test_create(self):

        template_content = self.create_template_content()

        draft_text_mc = DraftTextMicroContent(
            template_content = template_content,
            microcontent_type = self.microcontent_type,
        )

        draft_text_mc.save()

        ldtmc = LocalizedDraftTextMicroContent.objects.create(draft_text_mc, self.app.primary_language,
                                                              self.content, self.user)

        ldtmc.refresh_from_db()

        self.assertEqual(ldtmc.microcontent, draft_text_mc)
        self.assertEqual(ldtmc.language, self.app.primary_language)
        self.assertEqual(ldtmc.content, self.content)
        self.assertEqual(ldtmc.creator, self.user)
        

    def test_get_content(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        ldtmc = draft_text_mc.get_localized(self.app.primary_language)

        content = ldtmc.get_content()
        self.assertEqual(content, self.content)
        

    def test_save(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        ldtmc = draft_text_mc.get_localized(self.app.primary_language)
        ldtmc.content = None
        
        ldtmc.save()
        
        self.assertEqual(ldtmc.plain_text, None)

        ldtmc.content = '<div>Test Content</div>'
        ldtmc.save()

        self.assertEqual(ldtmc.plain_text, 'Test Content')



class TestPublishedTextMicroContent(WithUser, WithApp, WithTemplateContent, WithDraftTextMicroContent, TestCase):


    def test_create(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        published_text_mc = PublishedTextMicroContent.objects.create(draft_text_mc)

        published_text_mc.refresh_from_db()

        self.assertEqual(published_text_mc.template_content, template_content)
        self.assertEqual(published_text_mc.microcontent_type, self.microcontent_type)


    def test_get_language_dependant(self):

        template_content = self.create_template_content()

        draft_text_mc = self.create_draft_text_mc(template_content)

        draft_text_mc.publish([self.app.primary_language])

        published_text_mc = PublishedTextMicroContent.objects.get(template_content=template_content,
                                                        microcontent_type=self.microcontent_type)

        contents = PublishedTextMicroContent.objects.get_language_dependant(template_content, self.microcontent_type,
                                                        self.app.primary_language)

        lptmc = LocalizedPublishedTextMicroContent.objects.get(microcontent=published_text_mc)

        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0], lptmc)
        

    def test_get_locale_model(self):

        LocaleModel = PublishedTextMicroContent.get_locale_model()
        self.assertEqual(LocaleModel, LocalizedPublishedTextMicroContent)
        

    def test_get_content(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        draft_text_mc.publish([self.app.primary_language])

        published_text_mc = PublishedTextMicroContent.objects.get(template_content=template_content,
                                                        microcontent_type=self.microcontent_type)

        content = published_text_mc.get_content(self.app.primary_language)
        self.assertEqual(content, self.content)
    

    def test_get_localized(self):

        template_content = self.create_template_content()
        draft_text_mc = self.create_draft_text_mc(template_content)

        draft_text_mc.publish([self.app.primary_language])

        published_text_mc = PublishedTextMicroContent.objects.get(template_content=template_content,
                                                        microcontent_type=self.microcontent_type)

        lptmc = published_text_mc.get_localized(self.app.primary_language)
        expected_lptmc = LocalizedPublishedTextMicroContent.objects.get(microcontent=published_text_mc,
                                                                        language=self.app.primary_language)

        self.assertEqual(lptmc, expected_lptmc)

        non_existant_lptmc = published_text_mc.get_localized('fr')
        self.assertEqual(non_existant_lptmc, None)



class TestLocalizedPublishedTextMicroContent(WithUser, WithApp, WithTemplateContent, WithDraftTextMicroContent,
                                             TestCase):


    def create_localized_published_mc(self, template_content):

        draft_text_mc = self.create_draft_text_mc(template_content)

        published_text_mc = PublishedTextMicroContent.objects.create(draft_text_mc)


        lptmc = LocalizedPublishedTextMicroContent.objects.create(published_text_mc, self.app.primary_language,
                                                                  self.content, self.user)

        return lptmc, published_text_mc
    

    def test_create(self):

        template_content = self.create_template_content()
        
        lptmc, published_text_mc = self.create_localized_published_mc(template_content)

        lptmc.refresh_from_db()

        self.assertEqual(lptmc.language, self.app.primary_language)
        self.assertEqual(lptmc.microcontent, published_text_mc)
        self.assertEqual(lptmc.content, self.content)
        self.assertEqual(lptmc.creator, self.user)
        

    def test_get_content(self):

        template_content = self.create_template_content()

        lptmc, published_text_mc = self.create_localized_published_mc(template_content)

        lptmc.refresh_from_db()

        content = lptmc.get_content()
        self.assertEqual(content, self.content)


    def test_save(self):

        template_content = self.create_template_content()
        
        lptmc, published_text_mc = self.create_localized_published_mc(template_content)

        lptmc.content = None
        lptmc.save()
        
        self.assertEqual(lptmc.plain_text, None)

        lptmc.content = '<div>Test Content</div>'
        lptmc.save()

        self.assertEqual(lptmc.plain_text, 'Test Content')


# Testing Images
# -> take care of licences
from content_licencing.models import ContentLicenceRegistry

class WithImageMicroContent:

    image_microcontent_type = 'test_image'

    licence = 'CC0'
    creator_name = 'Someone With a Name'

    filename = 'test_image.jpg'

    def get_content(self):
        content = SimpleUploadedFile(name=self.filename, content=open(TEST_IMAGE_PATH, 'rb').read(),
                                     content_type='image/jpeg')

        return content


    def create_draft_image_mc(self, template_content):

        image = self.get_content()

        draft_image_mc = DraftImageMicroContent.objects.create(template_content, self.app.primary_language,
                                    self.image_microcontent_type, image, self.user)

        ldimc = draft_image_mc.get_localized(self.app.primary_language)
        # set licence
        licence_kwargs = {
            'creator_name' : self.creator_name,
        }
        registry_entry = ContentLicenceRegistry.objects.register(ldimc, 'content', self.user, self.licence, '1.0',
                            **licence_kwargs)

        return draft_image_mc
    

@test_settings
class TestDraftImageMicroContent(WithUser, WithApp, WithTemplateContent, WithMedia, WithImageMicroContent, TestCase):    

    def test_create(self):

        template_content = self.create_template_content()

        image = self.get_content()

        draft_image_mc = DraftImageMicroContent.objects.create(template_content, self.app.primary_language,
                                    self.image_microcontent_type, image, self.user)

        draft_image_mc.refresh_from_db()

        self.assertEqual(draft_image_mc.template_content, template_content)
        self.assertEqual(draft_image_mc.microcontent_type, self.image_microcontent_type)

        ldimc = LocalizedDraftImageMicroContent.objects.get(microcontent=draft_image_mc)

        self.assertEqual(ldimc.language, self.app.primary_language)
        self.assertEqual(ldimc.creator, self.user)


    def test_get_language_dependant(self):

        template_content = self.create_template_content()

        draft_image_mc = self.create_draft_image_mc(template_content)

        contents = DraftImageMicroContent.objects.get_language_dependant(template_content,
                                                self.image_microcontent_type, self.app.primary_language)

        ldimc = LocalizedDraftImageMicroContent.objects.get(microcontent=draft_image_mc)

        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0], ldimc)
        

    def test_get_form_field(self):
        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)
        ldimc = LocalizedDraftImageMicroContent.objects.get(microcontent=draft_image_mc)

        widget_attrs_default = {
            'language' : self.app.primary_language,
            'data-microcontentcategory' : 'image',
            'data-microcontenttype' : 'single_image',
        }

        widget_attrs = widget_attrs_default.copy()
        form_field = draft_image_mc.get_form_field(self.app, template_content, widget_attrs)

        self.assertTrue(isinstance(form_field, forms.ImageField))
        self.assertTrue(isinstance(form_field.widget, forms.FileInput))
        self.assertEqual(form_field.widget.attrs['file'], ldimc.content)

        # without ldimc
        ldimc.delete()
        draft_image_mc.refresh_from_db()

        widget_attrs = widget_attrs_default.copy()
        form_field_2 = draft_image_mc.get_form_field(self.app, template_content, widget_attrs)
        self.assertTrue(isinstance(form_field_2, forms.ImageField))
        
        self.assertTrue(isinstance(form_field_2.widget, forms.FileInput))
        self.assertFalse('file' in form_field_2.widget.attrs)
        

    def test_translation_complete(self):
        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)

        errors = draft_image_mc.translation_complete(self.app.primary_language)
        self.assertEqual(errors, [])
    

    def test_set_content(self):

        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)

        ldimc = LocalizedDraftImageMicroContent.objects.get(microcontent=draft_image_mc)

        old_path = ldimc.content.path
        self.assertTrue(os.path.isfile(old_path))

        image = SimpleUploadedFile(name='new_test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        draft_image_mc.set_content(image, self.user, self.app.primary_language)

        ldimc.refresh_from_db()
        self.assertFalse(os.path.isfile(old_path))
        self.assertTrue(os.path.isfile(ldimc.content.path))


        draft_image_mc.set_content(image, self.user, 'en')
        ldimc_en = LocalizedDraftImageMicroContent.objects.get(microcontent=draft_image_mc, language='en')

        self.assertTrue(os.path.isfile(ldimc_en.content.path))


    def test_get_publication_model(self):
        PublicationModel = DraftImageMicroContent.get_publication_model()
        self.assertEqual(PublicationModel, PublishedImageMicroContent)
        

    def test_get_locale_model(self):
        LocaleModel = DraftImageMicroContent.get_locale_model()
        self.assertEqual(LocaleModel, LocalizedDraftImageMicroContent)
        

    def test_publish(self):
        # also check the licences

        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)


        draft_image_mc.publish([self.app.primary_language])

        published_image_mc = PublishedImageMicroContent.objects.get(template_content=template_content,
                    microcontent_type=draft_image_mc.microcontent_type)

        ldimc = draft_image_mc.get_localized(self.app.primary_language)
        lpimc = published_image_mc.get_localized(self.app.primary_language)

        self.assertEqual(os.path.basename(ldimc.content.name), os.path.basename(lpimc.content.name))
        self.assertTrue(os.path.isfile(lpimc.content.path))

        draft_licence = ldimc.licences.all().first()
        published_licence = lpimc.licences.all().first()

        self.assertEqual(draft_licence.content_licence().short_name, published_licence.content_licence().short_name)
        self.assertEqual(draft_licence.creator_name, published_licence.creator_name)
    

    def test_get_content(self):

        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)

        content = draft_image_mc.get_content(self.app.primary_language)
        ldimc = draft_image_mc.get_localized(self.app.primary_language)

        self.assertEqual(content, ldimc.content)

        content_en = draft_image_mc.get_content('en')
        self.assertEqual(content_en, None)
    

    def test_get_localized(self):

        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)

        expected_ldimc = LocalizedDraftImageMicroContent.objects.get(microcontent=draft_image_mc)

        ldimc = draft_image_mc.get_localized(self.app.primary_language)

        self.assertEqual(ldimc, expected_ldimc)


@test_settings
class TestLocalizedDraftImageMicroContent(WithUser, WithApp, WithTemplateContent, WithMedia, WithImageMicroContent,
                                          TestCase):

    def test_create(self):

        template_content = self.create_template_content()

        draft_image_mc = DraftImageMicroContent(
            template_content = template_content,
            microcontent_type = self.image_microcontent_type,
        )

        draft_image_mc.save()

        content = self.get_content()
        ldimc = LocalizedDraftImageMicroContent.objects.create(draft_image_mc, self.app.primary_language, content,
                                                               self.user)

        ldimc.refresh_from_db()

        self.assertEqual(ldimc.microcontent, draft_image_mc)
        self.assertEqual(ldimc.language, self.app.primary_language)
        self.assertEqual(os.path.basename(ldimc.content.name), self.filename)
        self.assertEqual(ldimc.creator, self.user)

    
    def test_get_content(self):

        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)

        ldimc = draft_image_mc.get_localized(self.app.primary_language)

        content = ldimc.get_content()
        self.assertEqual(content, ldimc.content)


@test_settings
class TestPublishedImageMicroContent(WithUser, WithApp, WithTemplateContent, WithMedia, WithImageMicroContent,
                                     TestCase):

    def test_create(self):
        template_content = self.create_template_content()
        draft_image_mc = self.create_draft_image_mc(template_content)

        published_image_mc = PublishedImageMicroContent.objects.create(draft_image_mc)

        published_image_mc.refresh_from_db()

        self.assertEqual(published_image_mc.template_content, template_content)
        self.assertEqual(published_image_mc.microcontent_type, self.image_microcontent_type)
        

    def test_get_language_dependant(self):

        template_content = self.create_template_content()

        draft_image_mc = self.create_draft_image_mc(template_content)

        draft_image_mc.publish([self.app.primary_language])

        published_image_mc = PublishedImageMicroContent.objects.get(template_content=template_content,
                                                        microcontent_type=self.image_microcontent_type)

        contents = PublishedImageMicroContent.objects.get_language_dependant(template_content,
                                                self.image_microcontent_type, self.app.primary_language)

        lpimc = LocalizedPublishedImageMicroContent.objects.get(microcontent=published_image_mc)

        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0], lpimc)
        

    def test_get_locale_model(self):
        LocaleModel = PublishedImageMicroContent.get_locale_model()
        self.assertEqual(LocaleModel, LocalizedPublishedImageMicroContent)
        

    def test_get_content(self):

        template_content = self.create_template_content()

        draft_image_mc = self.create_draft_image_mc(template_content)

        draft_image_mc.publish([self.app.primary_language])

        published_image_mc = PublishedImageMicroContent.objects.get(template_content=template_content,
                                                        microcontent_type=self.image_microcontent_type)

        content = published_image_mc.get_content(self.app.primary_language)

        lpimc = published_image_mc.get_localized(self.app.primary_language)

        self.assertEqual(content, lpimc.content)
        

    def test_get_localized(self):

        template_content = self.create_template_content()

        draft_image_mc = self.create_draft_image_mc(template_content)

        draft_image_mc.publish([self.app.primary_language])

        published_image_mc = PublishedImageMicroContent.objects.get(template_content=template_content,
                                                        microcontent_type=self.image_microcontent_type)

        lpimc = published_image_mc.get_localized(self.app.primary_language)

        expected_lpimc = LocalizedPublishedImageMicroContent.objects.get(microcontent=published_image_mc,
                                                                         language=self.app.primary_language)

        self.assertEqual(lpimc, expected_lpimc)


@test_settings
class TestLocalizedPublishedImageMicroContent(WithUser, WithApp, WithTemplateContent, WithMedia,
                                              WithImageMicroContent, TestCase):

    def create_localized_published_mc(self, template_content):

        draft_image_mc = self.create_draft_image_mc(template_content)

        published_image_mc = PublishedImageMicroContent.objects.create(draft_image_mc)

        content = self.get_content()
        lpimc = LocalizedPublishedImageMicroContent.objects.create(published_image_mc, self.app.primary_language,
                                                                   content, self.user)

        return lpimc, published_image_mc
    

    def test_create(self):

        template_content = self.create_template_content()
        
        lpimc, published_image_mc = self.create_localized_published_mc(template_content)

        lpimc.refresh_from_db()

        self.assertEqual(lpimc.language, self.app.primary_language)
        self.assertEqual(lpimc.microcontent, published_image_mc)
        self.assertEqual(os.path.basename(lpimc.content.name), self.filename)
        self.assertEqual(lpimc.creator, self.user)
        

    def test_get_content(self):

        template_content = self.create_template_content()

        lpimc, published_image_mc = self.create_localized_published_mc(template_content)

        lpimc.refresh_from_db()

        content = lpimc.get_content()
        self.assertEqual(content, lpimc.content)
