from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .widgets import CropImageInput


class LocalizeableForm(forms.Form):

    input_language = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop('language', None)
        super().__init__(*args, **kwargs)

        self.fields['input_language'].initial = self.language

        for field_name in self.localizeable_fields:
            self.fields[field_name].language = self.language



class LocalizeableModelForm(forms.ModelForm):

    input_language = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop('language', None)
        super().__init__(*args, **kwargs)

        self.fields['input_language'].initial = self.language

        for field_name in self.localizeable_fields:
            self.fields[field_name].language = self.language


from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, get_user_model
User = get_user_model()
class EmailOrUsernameAuthenticationForm(AuthenticationForm):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = _('Username or e-mail')

    def clean(self):
        username = self.cleaned_data.get('username', None)
        password = self.cleaned_data.get('password', None)
        

        if username and password:

            if "@" in username:
                user_pre = User.objects.filter(email=username).first()

                if user_pre:
                    username = user_pre.username
                else:
                    raise forms.ValidationError(_('No user found by that email address'))
                
            self.user_cache = authenticate(username=username, password=password)
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
        return self.cleaned_data


'''
    ManageContentImageForm
    - used by online_content and app_kit
    - add an image to any content of the app, or an app directly
    - images have a type, default is 'image', possible types are eg 'background' or 'logo'
    - app, content_type and object_id are in view_kwargs
'''
from collections import OrderedDict
import hashlib, json
class ManageContentImageFormCommon:

    licencing_model_field = 'source_image'

    def __init__(self, *args, **kwargs):
        self.current_image = kwargs.pop('current_image', None)
        super().__init__(*args, **kwargs)

        # get the source_image field
        source_image_field = self.get_source_image_field()

        self.fields['source_image'] = source_image_field

        field_order = [
            'source_image',
            'image_type',
            'crop_parameters',
            'md5',
            'creator_name',
            'creator_link',
            'source_link',
            'licence',
        ]

        self.order_fields(field_order)

    
    def get_source_image_field(self):
        # unfortunately, a file field cannot be prepoluated due to html5 restrictions
        # therefore, source_image has to be optional. Otherwise, editing would be impossible
        # check if a new file is required in clean
        source_image_field = forms.ImageField(widget=CropImageInput, required=False)
        source_image_field.widget.current_image = self.current_image

        return source_image_field


    def order_fields(self, field_order):
        """
        Rearranges the fields according to field_order.

        field_order is a list of field names specifying the order. Fields not
        included in the list are appended in the default order for backward
        compatibility with subclasses not overriding field_order. If field_order
        is None, all fields are kept in the order defined in the class.
        Unknown fields in field_order are ignored to allow disabling fields in
        form subclasses without redefining ordering.
        """
        if field_order is None:
            return
        fields = OrderedDict()
        for key in field_order:
            try:
                fields[key] = self.fields.pop(key)
            except KeyError:  # ignore unknown fields
                pass
        fields.update(self.fields)  # add remaining fields in original order
        self.fields = fields


    # "{"x":0,"y":0,"width":0,"height":0,"rotate":0}" is invalid
    def clean_crop_parameters(self):
        crop_parameters = self.cleaned_data.get('crop_parameters')
        
        if crop_parameters:
            loaded_crop_parameters = json.loads(crop_parameters)
            width = loaded_crop_parameters.get('width', 0)
            height = loaded_crop_parameters.get('height', 0)

            if width == 0 or height == 0:
                del self.cleaned_data['crop_parameters']
                raise forms.ValidationError(_('You selected an invalid area of the image.'))

        return crop_parameters
        
    # if an image is present, at least crop_parameters and creator_name have to be present
    def clean(self):
        cleaned_data = super().clean()
        
        file_ = cleaned_data.get('source_image', None)

        if file_ is not None and file_:
            
            md5 = cleaned_data.get('md5', None)

            file_md5 = hashlib.md5(file_.read()).hexdigest()

            if md5:
                if file_md5 != md5:
                    raise forms.ValidationError(_('The image upload was not successful. Please try again'))

            else:
                cleaned_data['md5'] = file_md5
        
        return cleaned_data

