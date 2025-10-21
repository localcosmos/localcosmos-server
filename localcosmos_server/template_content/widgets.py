from django.forms.widgets import Input, FileInput, Textarea

class FileContentWidget(FileInput):
    template_name = 'template_content/widgets/filecontent_field.html'

class ContentWithPreviewWidget(Input):
    template_name = 'template_content/widgets/content_with_preview.html'

class TextareaContentWidget(Textarea):
    template_name = 'template_content/widgets/textarea.html'

class TextContentWidget(Textarea):
    template_name = 'template_content/widgets/text.html'
    
# this just shows a button with the components that can be added 
class StreamContentWidget(Input):
    template_name = 'template_content/widgets/stream_content.html'
        
    def __init__(self, app, localized_template_content, content_key, content_definition, attrs=None):
        self.app = app
        self.localized_template_content = localized_template_content
        self.content_key = content_key
        self.content_definition = content_definition
        super().__init__(attrs)
        
        
    def get_stream_items(self):
        if self.localized_template_content and self.localized_template_content.draft_contents:
            if self.content_key in self.localized_template_content.draft_contents:
                return self.localized_template_content.draft_contents[self.content_key]
        return []
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['app'] = self.app
        context['widget']['localized_template_content'] = self.localized_template_content
        context['widget']['content_key'] = self.content_key
        context['widget']['content_definition'] = self.content_definition
        context['widget']['stream_items'] = self.get_stream_items()
        return context