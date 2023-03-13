from django.forms import Field

from .widgets import ComponentWidget

class ComponentField(Field):
    widget = ComponentWidget