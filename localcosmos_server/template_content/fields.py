from django.forms import Field

from .widgets import ContentWithPreviewWidget, StreamContentWidget

class ComponentField(Field):
    widget = ContentWithPreviewWidget

class StreamField(Field):
    widget = StreamContentWidget
