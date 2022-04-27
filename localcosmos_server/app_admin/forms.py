from django import forms
from django.utils.translation import gettext_lazy as _


from localcosmos_server.models import APP_USER_ROLES

choices = list(APP_USER_ROLES)
choices.append(('user', _('user')))

class AppUserRoleForm(forms.Form):
    role = forms.ChoiceField(choices=choices)


class SearchAppUserForm(forms.Form):
    search_user = forms.CharField(label=_('Search users'), required=False)
