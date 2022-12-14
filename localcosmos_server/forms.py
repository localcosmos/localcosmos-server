from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .widgets import CropImageInput, ImageInputWithPreview

VALID_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']#, 'svg']
from django.core.validators import FileExtensionValidator


class FormLocalizationMixin:
    
    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop('language', None)
        super().__init__(*args, **kwargs)

        self.fields['input_language'].initial = self.language

        for field_name in self.localizeable_fields:
            self.fields[field_name].language = self.language


class LocalizeableForm(FormLocalizationMixin, forms.Form):

    input_language = forms.CharField(widget=forms.HiddenInput)



class LocalizeableModelForm(FormLocalizationMixin, forms.ModelForm):

    input_language = forms.CharField(widget=forms.HiddenInput)



from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, get_user_model
User = get_user_model()
class EmailOrUsernameAuthenticationForm(AuthenticationForm):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = _('Username or email address')

    def clean(self):
        username = self.cleaned_data.get('username', None)
        password = self.cleaned_data.get('password', None)
        

        if username and password:

            # username might contain @
            if '@' in username:
                user_pre = User.objects.filter(email=username).first()

                if not user_pre:
                    user_pre = User.objects.filter(username=username).first()

                if user_pre:
                    username = user_pre.username
                else:
                    raise forms.ValidationError(_('Invalid username or email address'))
                
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
    - used by template_content and app_kit
    - expects LicencingFormMixin in Form
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
        self.content_instance = kwargs.pop('content_instance', None)
        super().__init__(*args, **kwargs)

        # get the source_image field
        source_image_field = self.get_source_image_field()

        self.fields['source_image'] = source_image_field

        field_order = [
            'source_image',
            'image_type',
            'crop_parameters',
            'features',
            'md5',
            'creator_name',
            'creator_link',
            'source_link',
            'licence',
            'requires_translation',
        ]

        self.order_fields(field_order)

    
    def get_source_image_field(self):
        # unfortunately, a file field cannot be prepoluated due to html5 restrictions
        # therefore, source_image has to be optional. Otherwise, editing would be impossible
        # check if a new file is required in clean

        # read optional restrictions from the model using image_type
        restrictions = {}

        image_type = self.initial.get('image_type', 'image')

        if 'image_type' in self.data:
            image_type = self.data['image_type']

        if hasattr(self, 'cleaned_data'):
            image_type = self.cleaned_data.get('image_type', image_type)

        restrictions = {}

        if self.content_instance and hasattr(self.content_instance, 'get_content_image_restrictions'):
            restrictions = self.content_instance.get_content_image_restrictions(image_type)


        allow_features = restrictions.get('allow_features', True)
        allow_cropping = restrictions.get('allow_cropping', True)

        widget_kwargs = {
            'restrictions' : restrictions,
        }

        valid_file_types = VALID_IMAGE_EXTENSIONS

        field_class = forms.ImageField

        widget_class = CropImageInput

        if allow_features == False and allow_cropping == False:
            widget_class = ImageInputWithPreview


        # no cropping for svgs
        if 'file_type' in restrictions:
            valid_file_types = restrictions['file_type']
            
            # fall back to simple image with preview for svg
            if 'svg' in restrictions['file_type']:
                field_class = forms.FileField
                widget_class = ImageInputWithPreview


        if widget_class == ImageInputWithPreview and 'crop_parameters' in self.fields:
             self.fields['crop_parameters'].required = False

        widget=widget_class(**widget_kwargs)
           

        source_image_field = field_class(widget=widget, required=False,
                                              validators=[FileExtensionValidator(valid_file_types)])
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


    def clean_features(self):

        features = self.cleaned_data.get('features')

        if (isinstance(features, str)):

            # prevent storing an empty string in the db
            if len(features) > 0:
                features = json.loads(features)
            else:
                features = None

        if features:
            if isinstance(features, list) == False:
                del self.cleaned_data['features']
                raise forms.ValidationError(_('Invalid features drawn on canvas.'))

        return features

        
    # if an image is present, at least crop_parameters and creator_name have to be present
    def clean(self):
        cleaned_data = super().clean()
        
        file_ = cleaned_data.get('source_image', None)

        if file_ is not None and file_:
            
            md5 = cleaned_data.get('md5', None)

            file_md5 = hashlib.md5(file_.read()).hexdigest()

            # this line is extremely required. do not delete it. otherwise the file_ will not be read correctly
            file_.seek(0)

            if md5:
                if file_md5 != md5:
                    raise forms.ValidationError(_('The image upload was not successful. Please try again.'))

            else:
                cleaned_data['md5'] = file_md5
        
        return cleaned_data


from content_licencing.mixins import LicencingFormMixin, OptionalLicencingFormMixin
from localcosmos_server.widgets import HiddenJSONInput
class ManageContentImageForm(ManageContentImageFormCommon, LicencingFormMixin):
    
    # cropping
    crop_parameters = forms.CharField(widget=forms.HiddenInput)

    # features like arrows
    features = forms.CharField(widget=HiddenJSONInput, required=False)

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput, required=False)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)

    requires_translation = forms.BooleanField(required=False)
    

    def clean_source_image(self):

        source_image = self.cleaned_data.get('source_image')
        if not source_image and not self.current_image:
            raise forms.ValidationError('An image file is required.')

        return source_image


class ManageContentImageWithTextForm(FormLocalizationMixin, ManageContentImageForm):

    input_language = forms.CharField(widget=forms.HiddenInput)

    text = forms.CharField(max_length=355, required=False, widget=forms.Textarea,
                           help_text=_('Text that will be shown together with this image.'))

    localizeable_fields = ['text']
    layoutable_simple_fields = ['text']


class ManageLocalizedContentImageForm(ManageContentImageForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['requires_translation']


'''
    A form with an optional ContentImage. If the user uploads an image, creator_name and licence have to be present
'''
class OptionalContentImageForm(ManageContentImageFormCommon, OptionalLicencingFormMixin):

    # cropping
    crop_parameters = forms.CharField(widget=forms.HiddenInput, required=False)

    # features like arrows
    features = forms.CharField(widget=HiddenJSONInput, required=False)

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput, required=False)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)

    # if suggested images are provided, the user may click on the suggested image
    referred_content_image_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def fields_required(self, fields):
        """Used for conditionally marking fields as required."""
        for field in fields:
            if not self.cleaned_data.get(field, None):
                msg = forms.ValidationError(_('This field is required.'))
                self.add_error(field, msg)


    # if an image is present, at least crop_parameters, licence and creator_name have to be present
    def clean(self):
        cleaned_data = super().clean()
        file_ = cleaned_data.get('source_image', None)

        if file_ is not None:
            self.fields_required(['creator_name', 'licence'])
            
        
        return cleaned_data