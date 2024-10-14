from localcosmos_server.template_content.models import (TemplateContent, LocalizedTemplateContent, Navigation,
    )

import uuid

PAGE_TEMPLATE_TYPE = 'page'
TEST_TEMPLATE_NAME = 'TestPage'

TEST_PAGE_CONTENT_KEYS = ['image', 'longText', 'component', 'text']
TEST_PAGE_CONTENT_TYPES = {
    'image': 'image',
    'longText': 'text',
    'component': 'component',
    'text': 'text',
}

class WithTemplateContent:

    def setUp(self):
        super().setUp()
        self.template_content_title = 'Test template content'
        self.template_content = TemplateContent.objects.create(self.user, self.app,
            self.app.primary_language, self.template_content_title, TEST_TEMPLATE_NAME, PAGE_TEMPLATE_TYPE)
        
        self.primary_ltc = self.template_content.get_locale(self.app.primary_language)
        
        
    def get_contents(self):
        template = self.primary_ltc.template_content.draft_template
        template.load_template_and_definition_from_files()
        contents = template.definition['contents']
        
        return contents

    def create_localized_template_content(self, user, template_content=None, language='en',
                                          draft_title='draft title'):
        
        if not template_content:
            template_content = self.template_content
        
        ltc = LocalizedTemplateContent.objects.create(user, template_content, language, draft_title)
        
        return ltc
    
    
    def fill_localized_template_content(self, localized_template_content=None):
        
        if not localized_template_content:
            localized_template_content = self.primary_ltc
        
        component_uuid = str(uuid.uuid4())
        component_2_uuid = str(uuid.uuid4())
        
        component = {
            'uuid': component_uuid,
            'text': 'component text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': 'component link title',
                'url': '/test-url/', # just for testing
            }
        }
        
        component_2 = {
            'uuid': component_2_uuid,
            'text': 'component text 2',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': 'component 2 link title',
                'url': '/test-url-2/', # just for testing
            }
        }
        
        localized_template_content.draft_contents = {
            'longText': 'test text which is a bit longer',
            'text': 'short text',
            'link': {
                'pk': str(self.primary_ltc.pk),
                'slug': self.primary_ltc.slug,
                'templateName': self.primary_ltc.template_content.draft_template_name,
                'title': 'link title',
                'url': '/test-url/', # just for testing
            },
            'component': [
                component,
            ],
            'component2': component_2,
        }
        
        localized_template_content.save()
        