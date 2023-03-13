from django.forms.widgets import Input, FileInput, Textarea

class ComponentWidget(Input):
    input_type = 'text'
    template_name = 'template_content/widgets/component_field.html'

class FileContentWidget(FileInput):
    template_name = 'template_content/widgets/filecontent_field.html'


class ContentWithPreviewWidget(Input):
    template_name = 'template_content/widgets/content_with_preview.html'

class TextareaContentWidget(Textarea):
    template_name = 'template_content/widgets/textarea.html'

class TextContentWidget(Textarea):
    template_name = 'template_content/widgets/text.html'
