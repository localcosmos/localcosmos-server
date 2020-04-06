from django import forms
from django.utils.translation import gettext_lazy as _

from localcosmos_server.models import App

from django.core.validators import FileExtensionValidator
class InstallAppForm(forms.Form):
    zipfile = forms.FileField(label=_('App .zip file'),
                              validators=[FileExtensionValidator(allowed_extensions=['zip'])])

    url = forms.URLField(label=_('URL of this app'),
                help_text=_('Absolute URL where your app will be served according to your web server configuration.'),
                         widget=forms.TextInput(attrs={'placeholder':_('e.g. mysite.com or mysite.com/app')}))


class EditAppForm(forms.ModelForm):

    class Meta:
        model = App
        fields=('url', )
