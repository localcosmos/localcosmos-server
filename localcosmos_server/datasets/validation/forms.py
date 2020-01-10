from django import forms
from django.utils.translation import gettext_lazy as _

VALIDATION_CHOICES = (
    ('is_valid', _('Observation is valid')),
    ('is_invalid', _('Observation is invalid')), 
)
class HumanInteractionValidationForm(forms.Form):
    dataset_is_valid = forms.ChoiceField(choices=VALIDATION_CHOICES, widget=forms.RadioSelect)

class ExpertReviewValidationForm(HumanInteractionValidationForm):
    comment = forms.CharField(required=False, widget=forms.Textarea)
