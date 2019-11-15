from django import forms
from django.utils.translation import ugettext_lazy as _

from django.core.validators import FileExtensionValidator
class InstallAppForm(forms.Form):
    zipfile = forms.FileField(label=_('App .zip file'),
                              validators=[FileExtensionValidator(allowed_extensions=['zip'])])

    url = forms.URLField(label=_('URL of this App'),
                help_text=_('absolute url where your app will be served according to your webserver configuration'),
                         widget=forms.TextInput(attrs={'placeholder':_('eg mysite.com or mysite.com/app')}))