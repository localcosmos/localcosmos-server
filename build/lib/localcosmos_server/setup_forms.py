# putting these forms in .forms.py creates a circular import
from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

'''
    create a superuser account with email
'''
from django.contrib.auth.forms import UserCreationForm, UsernameField

User = get_user_model()

class SetupSuperuserForm(UserCreationForm):

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'email_mismatch': _("The two email address fields didn't match."),
    }
    
    email = forms.EmailField(label=_('Email'))
    email2 = forms.EmailField(label = _('Email (again)'))

    def clean_email2(self):
        email = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('email2')
        if email and email2 and email != email2:
            raise forms.ValidationError(
                self.error_messages['email_mismatch'],
                code='email_mismatch',
            )
        
        return email2


    def save(self, commit=True):
        # create the superuser from ModelManager
        user = User.objects.create_superuser(self.cleaned_data['username'], self.cleaned_data['email'],
                                             self.cleaned_data['password1'])
        return user


    class Meta:
        model = User
        fields = ('username', 'email', 'email2')
        field_classes = {'username': UsernameField}

