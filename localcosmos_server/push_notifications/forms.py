import json

from django import forms
from django.utils.translation import gettext_lazy as _


class SendPushNotificationForm(forms.Form):

    title = forms.CharField(max_length=65, label=_('Title'))
    body = forms.CharField(max_length=240, widget=forms.Textarea(attrs={'rows': 4}), label=_('Message'))
    language_code = forms.ChoiceField(label=_('Language'), required=False)
    data = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, app, *args, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)
        self.fields['language_code'].choices = [
            ('', _('All languages')),
        ] + [(lang, lang) for lang in app.languages()]

    def clean_data(self):
        raw = self.cleaned_data.get('data', '')
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise forms.ValidationError(_('Data must be valid JSON.'))