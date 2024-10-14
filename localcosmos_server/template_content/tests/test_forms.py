from django.test import TestCase
from django import forms
from django.contrib.contenttypes.models import ContentType
from localcosmos_server.models import ServerContentImage

from localcosmos_server.template_content.forms import (CreateTemplateContentForm,
        TemplateContentFormFieldManager, ComponentFormFieldManager, ManageNavigationEntryForm,
        ManageLocalizedTemplateContentForm, ManageComponentForm, ManageNavigationForm,
        TranslateNavigationForm)

from localcosmos_server.template_content.models import (TemplateContent, LocalizedTemplateContent,
                            Navigation, NavigationEntry, LocalizedNavigationEntry)

from .mixins import WithTemplateContent, TEST_TEMPLATE_NAME, PAGE_TEMPLATE_TYPE

from localcosmos_server.tests.common import (test_settings,)
from localcosmos_server.tests.mixins import WithUser, WithApp, WithMedia, WithServerContentImage

import uuid

class TestCreateTemplateContentForm(WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        super().setUp()
    
    @test_settings
    def test_init(self):
        
        template_type = 'template'
        
        form = CreateTemplateContentForm(self.app)
        
        self.assertEqual(form.app, self.app)
        self.assertEqual(form.assignment, None)
    
        self.assertEqual(form.fields['template_name'].choices, [('TestPage', 'test-page')])
        
        form = CreateTemplateContentForm(self.app, assignment='home')
        
        self.assertEqual(form.assignment, 'home')
    
    
    @test_settings
    def test_clean(self):
        
        post_data = {
            'draft_title': 'draft test page',
            'template_name': 'TestPage',
            'input_language': 'de',
        }
        
        form = CreateTemplateContentForm(self.app, data=post_data)
        
        is_valid = form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        assignment = 'home'
        
        template_content = TemplateContent.objects.create(self.user, self.app,
            self.app.primary_language, 'Page title', TEST_TEMPLATE_NAME,
            PAGE_TEMPLATE_TYPE, assignment=assignment)
        
        form_2 = CreateTemplateContentForm(self.app, data=post_data)
        
        is_valid_2 = form.is_valid()
        
        self.assertEqual(form_2.errors, {})
        
        
        form_3 = CreateTemplateContentForm(self.app, assignment=assignment, data=post_data)
        
        is_valid_3 = form.is_valid()
        
        expected_errors = {'__all__': ['A template content for "home" already exists']}
        
        self.assertEqual(form_3.errors, expected_errors)


class TestTemplateContentFormFieldManager(WithTemplateContent, WithServerContentImage, WithMedia,
                                          WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
    # not for components
    def add_content_image(self, content_key):
        content_image = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        return content_image
    
    @test_settings
    def test_init(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        self.assertEqual(manager.app, self.app)
        self.assertEqual(manager.template_content, self.template_content)
        self.assertEqual(manager.localized_template_content, self.primary_ltc)
        self.assertEqual(manager.primary_locale_template_content, self.primary_ltc)
        
        secondary_ltc = self.create_localized_template_content(self.user)
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  secondary_ltc)
        
        self.assertEqual(manager.app, self.app)
        self.assertEqual(manager.template_content, self.template_content)
        self.assertEqual(manager.localized_template_content, secondary_ltc)
        self.assertEqual(manager.primary_locale_template_content, self.primary_ltc)
    
    @test_settings
    def test_get_instance(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        for content_key, content_definition in contents.items():
            content_type = content_definition['type']
            instances = manager.get_instances(content_key, content_type)
            
            self.assertEqual(instances, [])
            
        # add content for all content types
        self.fill_localized_template_content()
        
        # images: content _key of TestPage.json is "image"
        content_image = self.add_content_image('image')
        
        for content_key, content_definition in contents.items():
            
            if content_definition.get('allowMultiple', False) == False:
                content_type = content_definition['type']
                
                instance = manager.get_instance(content_key, content_type)

                self.assertFalse(type(instance) == list)

                if content_type == 'image':
                    self.assertEqual(instance, content_image)
                
                else:
                    self.assertEqual(instance, self.primary_ltc.draft_contents[content_key])
    
    @test_settings
    def test_get_instances(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        for content_key, content_definition in contents.items():
            content_type = content_definition['type']
            
            instances = manager.get_instances(content_key, content_type)
            
            self.assertEqual(instances, [])
            
        # add content for all content types
        self.fill_localized_template_content()
        content_image = self.add_content_image('images')
        
        for content_key, content_definition in contents.items():
            
            if content_definition.get('allowMultiple', False) == True:
                content_type = content_definition['type']
                instances = manager.get_instances(content_key, content_type)

                self.assertTrue(type(instances) == list)
                self.assertEqual(len(instances), 1)
                
                if content_type == 'image':
                    self.assertEqual(instances[0], content_image)
                else:
                    self.assertEqual(instances[0], self.primary_ltc.draft_contents[content_key][0])
    
    @test_settings
    def test_get_primary_locale_content(self):
        self.fill_localized_template_content()
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        content = manager.get_primary_locale_content('text')
        self.assertEqual(content, 'short text')
    
    
    @test_settings
    def test_add_primary_locale_content_to_form_field(self):
        self.fill_localized_template_content()
        
        field = forms.CharField()
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        field_w_content = manager._add_primary_locale_content_to_form_field(field, 'text')
        
        self.primary_ltc.refresh_from_db()
        self.assertEqual(field_w_content.primary_locale_content,
                         self.primary_ltc.draft_contents['text'])
        
        field_2 = forms.CharField()
        
        field_2_w_content = manager._add_primary_locale_content_to_form_field(field_2, 'nonexistant')
        
        self.assertEqual(field_2_w_content.primary_locale_content, None)
    
    
    @test_settings
    def test_get_form_fields(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        for content_key, content_definition in contents.items():
            form_fields = manager.get_form_fields(content_key, content_definition)
            
            if content_definition.get('allowMultiple', False) == True:
                self.assertEqual(form_fields[0]['field'].is_first, True)
                self.assertEqual(form_fields[-1]['field'].is_last, True)
                
                for field in form_fields:
                    self.assertEqual(field['field'].allow_multiple, True)
                    self.assertEqual(field['name'], content_key)
            else:
                
                field = form_fields[0]
                self.assertEqual(field['field'].allow_multiple, False)
                self.assertEqual(field['name'], content_key)
            
        
        self.fill_localized_template_content()
        
        for content_key, content_definition in contents.items():
            form_fields = manager.get_form_fields(content_key, content_definition)
            
            field_count = len(form_fields)

            if content_definition.get('allowMultiple', False) == True:
                self.assertEqual(form_fields[0]['field'].is_first, True)
                self.assertEqual(form_fields[-1]['field'].is_last, True)
                
                for counter, field in enumerate(form_fields, 1):
                    self.assertEqual(field['field'].allow_multiple, True)
                    
                    if counter == field_count:
                        self.assertEqual(field['name'], content_key, counter)
                    else:
                        self.assertEqual(field['name'], '{0}-{1}'.format(content_key, counter))
            else:
                
                field = form_fields[0]
                self.assertEqual(field['field'].allow_multiple, False)
                self.assertEqual(field['name'], content_key)
        
        
        # check maxNumber of component: maxNumber == 4
        component_uuids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
        
        for component_uuid in component_uuids:
            component = {
                'uuid': component_uuid,
                'text': 'component text',
                'link': {
                    'pk': str(self.primary_ltc.pk),
                    'slug': self.primary_ltc.slug,
                    'templateName': self.primary_ltc.template_content.draft_template_name,
                    'title': self.primary_ltc.published_title,
                    'url': '/test-url/', # just for testing
                }
            }
            
            
            self.primary_ltc.add_or_update_component('component', component)
            
        instances = manager.get_instances('component', 'component')
        self.assertEqual(len(instances), 4)
        
        max_fields = manager.get_form_fields('component', contents['component'])
        
        self.assertEqual(len(max_fields), 4)
        self.assertEqual(max_fields[0]['field'].is_first, True)
        self.assertEqual(max_fields[-1]['field'].is_last, True)
        
        for counter, component_field in enumerate(max_fields, 1):
            self.assertEqual(component_field['field'].allow_multiple, True)
            self.assertEqual(component_field['name'], 'component-{0}'.format(counter))
    
    @test_settings
    def test_get_label(self):
        
        content_key = 'longText'
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        label = manager._get_label(content_key, {})
        self.assertEqual(label, 'Long text')
        
        label = manager._get_label(content_key, {'label': 'Test label'})
        self.assertEqual(label, 'Test label')
        
    
    @test_settings
    def test_get_required(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        required = manager._get_required({})
        self.assertFalse(required)
    
    
    @test_settings
    def test_get_common_widget_attrs(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        for content_key, content_definition in contents.items():
            
            widget_attrs = manager._get_common_widget_attrs(content_key, content_definition, None)
            
            expected_widget_attrs = {
                'content_key' : content_key,
                'content_type' : content_definition['type'],
                'instance': None,
                'definition': content_definition,
            }
            
            self.assertEqual(widget_attrs, expected_widget_attrs)
            
    
    @test_settings
    def test_get_commn_field_kwargs(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        
        contents = self.get_contents()
        
        expected_values_map = {
            'help_text' : {
                'image' : 'Landscape image, approximately 2:1 ratio',
                'images' : 'Square image, exactly 1:1 ratio',
                'longText' : 'Describe your project',
                'text' : 'Short name of your App',
            },
            'label' : {
                'image' : 'Image',
                'images' : 'Images',
                'longText' : 'Long text',
                'component' : 'Component',
                'component2' : 'Component2',
                'text': 'Text',
                'link': 'Link',
            }
        }
        
        for content_key, content_definition in contents.items():
            
            field_kwargs = manager._get_common_field_kwargs(content_key, content_definition)
            
            expected_field_kwargs = {
                'required' : False,
                'label' : expected_values_map['label'][content_key],
                'help_text': expected_values_map['help_text'].get(content_key, None),
            }
            
            self.assertEqual(field_kwargs, expected_field_kwargs)
            
    
    @test_settings
    def test_get_image_type(self):
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        image_type = manager._get_image_type('testKey')
        self.assertEqual(image_type, 'testKey')
    
    
    @test_settings
    def test_get_image_form_field(self):
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        content_key = 'image'
        content_definition = contents['image']
        
        image_form_field = manager._get_image_form_field(content_key, content_definition)
        
        ltc_content_type = ContentType.objects.get_for_model(self.primary_ltc)
        
        # with current_image
        expected_widget_attrs = {
            'content_key': 'image',
            'content_type': 'image',
            'instance': None,
            'definition': content_definition,
            'data_url': '/app-admin/{0}/manage-template-content-image/{1}/{2}/image/'.format(
                self.app.uid, ltc_content_type.id, self.primary_ltc.pk),
            'delete_url': None,
            'accept': 'image/png, image/webp, image/jpeg'
        }
        
        self.assertEqual(image_form_field.widget.attrs, expected_widget_attrs)
        self.assertEqual(image_form_field.label, 'Image')
        self.assertEqual(image_form_field.required, False)
        self.assertEqual(image_form_field.help_text, content_definition['helpText'])
        
        self.assertEqual(image_form_field.primary_locale_content, None)
    
    @test_settings
    def test_get_image_form_field_w_image(self):
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        content_key = 'image'
        content_definition = contents['image']
        # add image
        content_image = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        image_form_field = manager._get_image_form_field(content_key, content_definition,
                                                         current_image=content_image)
        self.assertEqual(image_form_field.primary_locale_content, content_image)
        
        expected_widget_attrs = {
            'content_key': 'image',
            'content_type': 'image',
            'instance': content_image,
            'definition': content_definition,
            'data_url': '/app-admin/{0}/manage-template-content-image/{1}/'.format(
                self.app.uid, content_image.pk),
            'delete_url': '/app-admin/{0}/delete-template-content-image/{1}/'.format(
                self.app.uid, content_image.pk),
            'accept': 'image/png, image/webp, image/jpeg'
        }
        
        self.assertEqual(expected_widget_attrs, image_form_field.widget.attrs)
    
    
    @test_settings
    def test_get_image_form_field_allow_multiple(self):
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        content_key = 'images'
        content_definition = contents['images']
        
        images_form_field = manager._get_image_form_field(content_key, content_definition)
        
        ltc_content_type = ContentType.objects.get_for_model(self.primary_ltc)
        
        # with current_image
        expected_widget_attrs = {
            'content_key': 'images',
            'content_type': 'image',
            'instance': None,
            'definition': content_definition,
            'data_url': '/app-admin/{0}/manage-template-content-image/{1}/{2}/images/'.format(
                self.app.uid, ltc_content_type.id, self.primary_ltc.pk),
            'delete_url': None,
            'accept': 'image/png, image/webp, image/jpeg'
        }
        
        self.assertEqual(images_form_field.widget.attrs, expected_widget_attrs)
        self.assertEqual(images_form_field.label, 'Images')
        self.assertEqual(images_form_field.required, False)
        self.assertEqual(images_form_field.help_text, content_definition['helpText'])
        
        self.assertEqual(images_form_field.primary_locale_content, [])
        
        # add images
        content_image_2 = self.get_content_image(self.user, self.primary_ltc, content_key)
        content_image_3 = self.get_content_image(self.user, self.primary_ltc, content_key)
        
        image_form_field = manager._get_image_form_field(content_key, content_definition)
        self.assertEqual(image_form_field.primary_locale_content,
                         [content_image_2, content_image_3])
                
        
    @test_settings
    def test_get_text_form_field(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        content_key = 'text'
        content_definition = contents['text']
        
        text_field = manager._get_text_form_field(content_key, content_definition)
        
        self.assertEqual(text_field.widget.__class__.__name__, 'TextContentWidget')
        self.assertEqual(text_field.initial, '')
        self.assertEqual(text_field.primary_locale_content, None)
        
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        primary_locale_content = self.primary_ltc.draft_contents['text']
        
        text_field = manager._get_text_form_field(content_key, content_definition,
                                                  instance=primary_locale_content)
        
        self.assertEqual(text_field.widget.__class__.__name__, 'TextContentWidget')
        self.assertEqual(text_field.initial, primary_locale_content)
        self.assertEqual(text_field.primary_locale_content, primary_locale_content)
        
        
        # textarea
        content_key = 'longText'
        content_definition = contents['longText']
        
        long_text_field = manager._get_text_form_field(content_key, content_definition)
        self.assertEqual(long_text_field.widget.__class__.__name__, 'TextareaContentWidget')
    
    
    @test_settings
    def test_get_component_form_field(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        content_key = 'component'
        content_definition = contents['component']
        
        form_field = manager._get_component_form_field(content_key, content_definition)
        
        self.assertEqual(form_field.__class__.__name__, 'ComponentField')
        
        expected_widget_attrs = {
            'content_key': 'component',
            'content_type': 'component',
            'instance': None,
            'definition': content_definition,
            'data_url': '/app-admin/{0}/manage-component/{1}/component/'.format(
                self.app.uid, self.primary_ltc.pk),
            'delete_url': None,
            'preview_text': None
        }

        self.assertEqual(expected_widget_attrs, form_field.widget.attrs)
        
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        primary_locale_content = self.primary_ltc.draft_contents['component'][0]
        
        component_uuid = primary_locale_content['uuid']
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        form_field = manager._get_component_form_field(content_key, content_definition,
                                                       instance=primary_locale_content)
        
        expected_widget_attrs = {
            'content_key': 'component',
            'content_type': 'component',
            'instance': primary_locale_content,
            'definition': content_definition,
            'data_url': '/app-admin/{0}/manage-component/{1}/component/{2}/'.format(
                self.app.uid, self.primary_ltc.pk, component_uuid),
            'delete_url': '/app-admin/{0}/delete-component/{1}/component/{2}/'.format(
                self.app.uid, self.primary_ltc.pk, component_uuid),
            'preview_text': 'component text'
        }
        
        self.assertEqual(form_field.widget.attrs, expected_widget_attrs)
    
    
    @test_settings
    def test_get_templateContentLink_form_field(self):
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        contents = self.get_contents()
        
        content_key = 'link'
        content_definition = contents['link']
        
        form_field = manager._get_templateContentLink_form_field(content_key, content_definition)
        
        self.assertEqual(form_field.__class__.__name__, 'ModelChoiceField')
        
        self.assertEqual(form_field.initial, None)
        self.assertEqual(form_field.primary_locale_content, None)
        
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        instance = self.primary_ltc.draft_contents['link']
        
        linked_ltc = LocalizedTemplateContent.objects.get(pk=instance['pk'])
        
        primary_locale_content = self.primary_ltc.draft_contents['link']
        
        manager = TemplateContentFormFieldManager(self.app, self.template_content, 
                                                  self.primary_ltc)
        
        form_field = manager._get_templateContentLink_form_field(content_key, content_definition,
                                                        instance=instance)
        
        self.assertEqual(form_field.initial, linked_ltc)
        self.assertEqual(form_field.primary_locale_content, primary_locale_content)
        
        
    
class TestComponentFormFieldManager(WithTemplateContent, WithServerContentImage, WithMedia,
                                          WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
        
    def add_content_image(self, image_type):
        content_image = self.get_content_image(self.user, self.primary_ltc, image_type)
        
        return content_image
        
        
    @test_settings
    def test_init(self):
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        component_key = 'component'
        component = self.primary_ltc.draft_contents[component_key][0]
        component_uuid = component['uuid']
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid, component)
        
        self.assertEqual(manager.template_content, self.template_content)
        self.assertEqual(manager.localized_template_content, self.primary_ltc)
        self.assertEqual(manager.component_key, component_key)
        self.assertEqual(manager.component_uuid, component_uuid)
        self.assertEqual(manager.component, component)
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid)
        
        self.assertEqual(manager.component, {})
    
    @test_settings
    def test_get_image_type(self):
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        contents = self.get_contents()
        
        component_key = 'component'
        component = self.primary_ltc.draft_contents[component_key][0]
        component_uuid = component['uuid']
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid, component)
        
        content_key = 'image'
        image_type = manager._get_image_type(content_key)
        
        expected_image_type = 'component:{0}:image'.format(component_uuid)
        
        self.assertEqual(image_type, expected_image_type)
        
    
    @test_settings
    def test_get_instance(self):
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        component_key = 'component'
        component = self.primary_ltc.draft_contents[component_key][0]
        component_uuid = component['uuid']
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid)
        
        content_key = 'text'
        content_type = 'text'
        instance = manager.get_instance(content_key, content_type)
        
        self.assertEqual(instance, None)
        
        # with component
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid, component)
        
        
        instance = manager.get_instance(content_key, content_type)
        expected_instance = self.primary_ltc.draft_contents['component'][0]['text']
        self.assertEqual(instance, expected_instance)
        
        # check for component image
        component_image_type = 'component:{0}:image'.format(component_uuid)
        content_image = self.add_content_image(component_image_type)
        instance = manager.get_instance('image', 'image')
        self.assertEqual(instance, content_image)
        
    
    @test_settings
    def test_get_instances(self):
        
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        component_key = 'component'
        component = self.primary_ltc.draft_contents[component_key][0]
        component_uuid = component['uuid']
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid)
        
        content_key = 'text'
        content_type = 'text'
        instances = manager.get_instances(content_key, content_type)
        
        self.assertEqual(instances, [])
        
        # with component
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid, component)
        
        
        instances = manager.get_instances(content_key, content_type)
        expected_instances = self.primary_ltc.draft_contents['component'][0]['text']
        self.assertEqual(instances, expected_instances)
        
        # check for component image
        component_image_type = 'component:{0}:image'.format(component_uuid)
        content_image = self.add_content_image(component_image_type)
        instances = manager.get_instances('image', 'image')
        self.assertEqual(instances, [content_image])
    
    
    @test_settings
    def test_get_primary_locale_content(self):
        
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        component_key = 'component'
        component = self.primary_ltc.draft_contents[component_key][0]
        component_uuid = component['uuid']
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid)
        
        content_key = 'text'
        self.assertEqual(manager.get_primary_locale_content(content_key), [])
    
    
    @test_settings
    def test_get_required(self):
        
        self.fill_localized_template_content()
        self.primary_ltc.refresh_from_db()
        
        component_key = 'component'
        
        component_template = self.template_content.get_component_template(component_key)
        
        component_template.load_template_and_definition_from_files()
        contents = component_template.definition['contents']
        
        component = self.primary_ltc.draft_contents[component_key][0]
        component_uuid = component['uuid']
        
        manager = ComponentFormFieldManager(self.app, self.template_content, self.primary_ltc,
                                            component_key, component_uuid)
        
        content_definition = contents['text']
        
        self.assertEqual(manager._get_required(content_definition), True)

        image_definition = contents['image']
        self.assertEqual(manager._get_required(image_definition), False)
    


class TestManageLocalizedTemplateContentForm(WithTemplateContent, WithServerContentImage,
                                             WithMedia, WithUser, WithApp, TestCase):
    
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
    
    @test_settings
    def test_init(self):
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content, self.primary_ltc)
        
        self.assertEqual(form.language, self.primary_ltc.language)
        self.assertEqual(form.app, self.app)
        self.assertEqual(form.template_content, self.template_content)
        self.assertEqual(form.localized_template_content, self.primary_ltc)
        self.assertEqual(form.layoutable_full_fields, set([]))
        self.assertEqual(form.layoutable_simple_fields, set(['longText']))
        
        self.assertTrue(len(form.fields) > 3)
        
        # init, no ltc
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content)
        self.assertEqual(len(form.fields), 2)
        self.assertIn('input_language', form.fields)
        self.assertIn('draft_title', form.fields)

    
    @test_settings
    def test_set_template_definition(self):
        
        expected_def = self.template_content.draft_template.definition
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content, self.primary_ltc)

        self.assertEqual(expected_def, form.template_definition)

        form.template_definition = None
        
        form.set_template_definition()
        
        self.assertEqual(form.template_definition, expected_def)
    
    @test_settings
    def test_get_form_field_manager(self):
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content, self.primary_ltc)

        manager = form.get_form_field_manager()
        
        self.assertTrue(isinstance(manager, TemplateContentFormFieldManager))
    
    @test_settings
    def test_set_form_fields_no_ltc(self):
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content)
        
        self.assertEqual(len(form.fields), 2)
        self.assertIn('input_language', form.fields)
        self.assertIn('draft_title', form.fields)
        
    
    @test_settings
    def test_set_form_fields_ltc(self):
        
        contents = self.get_contents()
        
        form = ManageLocalizedTemplateContentForm(self.app, self.template_content,
                                                  self.primary_ltc)
        
        for bound_field in form:
            
            field = bound_field.field
            
            if bound_field.name in ['input_language', 'draft_title']:
                continue            
            
            self.assertEqual(field.language, self.primary_ltc.language)
            
            content_key = field.content_key
            definition = contents[content_key]
            self.assertEqual(field.content_definition, definition)
            

class TestManageComponentForm(WithTemplateContent, WithServerContentImage,
                                             WithMedia, WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
        
    @test_settings
    def test_init(self):
        
        content_key = 'component'
        
        with self.assertRaises(ValueError):
            form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
                                    content_key)
        
        initial = {
            'uuid': uuid.uuid4()
        }
        form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
                                    content_key, initial=initial)
        
        self.assertEqual(form.content_key, content_key)
        self.assertEqual(form.component, None)
        
        self.fill_localized_template_content()
        component = self.primary_ltc.draft_contents[content_key][0]
        
        initial = {
            'uuid': component['uuid'],
        }
        form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
                                   content_key, component, initial=initial)
        
        self.assertEqual(form.content_key, content_key)
        self.assertEqual(form.component, component)
    
    
    @test_settings
    def test_set_template_definition(self):
        
        content_key = 'component'
        
        initial = {
            'uuid': uuid.uuid4(),
        }
        form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
                                    content_key, initial=initial)
        
        form.set_template_definition()
        
        component_template = self.template_content.get_component_template(content_key)
        
        component_template.load_template_and_definition_from_files()
        
        self.assertEqual(component_template.definition, form.template_definition)
    
    
    @test_settings
    def test_get_form_field_manager(self):
        
        content_key = 'component'
        
        initial = {
            'uuid': uuid.uuid4(),
        }
        form = ManageComponentForm(self.app, self.template_content, self.primary_ltc,
                                    content_key, initial=initial)
        
        manager = form.get_form_field_manager()
        
        self.assertTrue(isinstance(manager, ComponentFormFieldManager))
        
            
            
class TestManageNavigationForm(WithTemplateContent, WithServerContentImage, WithMedia, WithUser,
                               WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
        
    @test_settings
    def test_init(self):
        
        form = ManageNavigationForm(self.app)
        
        self.assertEqual(form.app, self.app)
        self.assertEqual(form.navigation, None)
        
        self.assertIn('input_language', form.fields)
        self.assertIn('name', form.fields)
        self.assertIn('navigation_type', form.fields)
        
        # according to apps settings.json
        expected_choices = [
            ('main', 'Main navigation'),
            ('more', 'More - Burger'),
            ('legal', 'Legal navigation'),
            ('deepnav', 'Deep navigation'),
        ]
        
        self.assertEqual(form.fields['navigation_type'].choices, expected_choices)
        
        
        navigation = Navigation.objects.create(self.app, 'main', 'de', 'Name')
        
        form = ManageNavigationForm(self.app, navigation=navigation)
        
        self.assertEqual(form.app, self.app)
        self.assertEqual(form.navigation, navigation)
    
    
    @test_settings
    def test_clean_navigation_type(self):
        
        post_data = {
            'navigation_type' : 'main',
        }
        
        form = ManageNavigationForm(self.app, data=post_data)
        form.is_valid()
        
        navigation_type = form.clean_navigation_type()
        self.assertEqual(navigation_type, 'main')
        
        navigation = Navigation.objects.create(self.app, 'main', 'de', 'Name')
        
        with self.assertRaises(forms.ValidationError):
            navigation_type = form.clean_navigation_type()


class TestManageNavigationEntryForm(WithTemplateContent, WithServerContentImage, WithMedia,
                                    WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
    
    @test_settings
    def test_init(self):
        
        navigation = Navigation.objects.create(self.app, 'main', 'de', 'Name')
        
        form = ManageNavigationEntryForm(navigation)
        
        self.assertEqual(form.navigation_entry, None)
        self.assertEqual(form.max_levels, 2)
        
        self.assertEqual(list(form.fields['parent'].queryset), [])
        
        # create toplevel navigation entry
        entry = NavigationEntry(navigation=navigation)
        entry.save()
        
        form = ManageNavigationEntryForm(navigation)
        self.assertEqual(form.navigation_entry, None)
        self.assertEqual(list(form.fields['parent'].queryset), [entry])
    
        # test deep nav
        d_nav = Navigation.objects.create(self.app, 'deepnav', 'de', 'Deep nav')
        d_entry_1 = NavigationEntry(navigation=d_nav)
        d_entry_1.save()
        
        d_entry_1_locale = LocalizedNavigationEntry(
            navigation_entry = d_entry_1,
            language = 'de',
            link_name = 'link 1',
        )
        
        d_entry_1_locale.save()
        
        d_entry_2 = NavigationEntry(navigation=d_nav, parent=d_entry_1)
        d_entry_2.save()
        
        d_entry_2_locale = LocalizedNavigationEntry(
            navigation_entry = d_entry_2,
            language = 'de',
            link_name = 'link 2',
        )
        
        d_entry_2_locale.save()
        
        locale = d_entry_1.get_locale('de')
        self.assertEqual(locale, d_entry_1_locale)
        
        form = ManageNavigationEntryForm(d_nav)
        self.assertEqual(form.navigation_entry, None)
        self.assertEqual(list(form.fields['parent'].queryset), [d_entry_1, d_entry_2])
        
        # test single level navs
        s_nav = Navigation.objects.create(self.app, 'more', 'de', 'Footer nav')
        
        form = ManageNavigationEntryForm(s_nav)
        
        self.assertEqual(form.navigation_entry, None)
        self.assertEqual(form.max_levels, 1)
        
        self.assertEqual(list(form.fields['parent'].queryset), [])
        
        # create toplevel navigation entry
        s_entry = NavigationEntry(navigation=s_nav)
        s_entry.save()
        
        form = ManageNavigationEntryForm(s_nav)
        self.assertEqual(form.navigation_entry, None)
        self.assertEqual(list(form.fields['parent'].queryset), [])
        


class TestTranslateNavigationForm(WithTemplateContent, WithServerContentImage, WithMedia,
                                    WithUser, WithApp, TestCase):
    
    def setUp(self):
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.server_content_image_type = ContentType.objects.get_for_model(ServerContentImage)
        super().setUp()
        
    @test_settings
    def test_init(self):
        
        navigation = Navigation.objects.create(self.app, 'main', 'de', 'Name')
        
        pln = navigation.get_locale('de')
        
        entry_1 = NavigationEntry(navigation=navigation)
        entry_1.save()
        
        entry_1_locale = LocalizedNavigationEntry(
            navigation_entry = entry_1,
            language = 'de',
            link_name = 'link 1',
        )
        
        entry_1_locale.save()
        
        form = TranslateNavigationForm(self.app, navigation, language='en')
        
        self.assertEqual(form.navigation, navigation)
        self.assertEqual(form.primary_language, 'de')
        self.assertEqual(form.language, 'en')
        
        self.assertEqual(form.primary_locale_navigation, pln)
        
        self.assertEqual(list(form.navigation_entries), [entry_1])
        
        self.assertEqual(form.localized_navigation, None)
        
    
    @test_settings
    def test_set_form_fields(self):
        
        navigation = Navigation.objects.create(self.app, 'main', 'de', 'Name')
        
        pln = navigation.get_locale('de')
        
        entry_1 = NavigationEntry(navigation=navigation)
        entry_1.save()
        
        entry_1_locale = LocalizedNavigationEntry(
            navigation_entry = entry_1,
            language = 'de',
            link_name = 'link 1',
        )
        
        entry_1_locale.save()
        
        form = TranslateNavigationForm(self.app, navigation, language='en')
        
        form.fields = {
            'name': forms.CharField(),
        }
        
        form.set_form_fields()
        
        entry_field_name = 'ne-{0}'.format(entry_1.pk)
        
        self.assertIn(entry_field_name, form.fields)
        self.assertEqual(len(form.fields), 2)
        
        field = form.fields[entry_field_name]
        
        self.assertEqual(field.language, 'en')
        self.assertEqual(field.navigation_entry, entry_1)
        self.assertEqual(field.primary_locale_text, 'link 1')