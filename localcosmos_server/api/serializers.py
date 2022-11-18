from rest_framework import serializers

from localcosmos_server.datasets.models import Dataset, DatasetImages, ObservationForm

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class TokenObtainPairSerializerWithClientID(TokenObtainPairSerializer):

    # required for linking client_ids with users
    client_id = serializers.CharField()
    platform = serializers.CharField()

'''
    private user serializer: only accessible for the account owner
    - details JSONField is still missing
'''
class AccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'uuid', 'username', 'first_name', 'last_name', 'email')


class RegistrationSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField(label=_('Password (again)'), write_only=True,
                                      style={'input_type': 'password', 'placeholder':_('Password (again)')})

    first_name = serializers.CharField(label=_('First name (optional)'), required=False)
    last_name = serializers.CharField(label=_('Surname (optional)'), required=False)
    email = serializers.EmailField(label=_('Email address'), style={'placeholder':'you@example.com'})
    email2 = serializers.EmailField(label=_('Email address (again)'), style={'placeholder':'you@example.com'})

    client_id = serializers.CharField(label='', style={'input_type': 'hidden',})
    platform = serializers.CharField(label='', style={'input_type': 'hidden',})
    app_uuid = serializers.CharField(label='', style={'input_type': 'hidden',})

    def validate_email(self, value):
        email_exists = User.objects.filter(email__iexact=value).exists()
        if email_exists:
            raise serializers.ValidationError(_('This email address is already registered.'))

        return value

    def validate(self, data):
        if data['email'] != data['email2']:
            raise serializers.ValidationError({'email2': _('The email addresses did not match.')})

        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': _('The passwords did not match.')})
        return data


    def get_initial(self):
        initial = super().get_initial()

        lc_initial = getattr(self, 'lc_initial', {})

        initial.update(lc_initial)

        return initial

    def create(self, validated_data):
        extra_fields = {}

        first_name = validated_data.get('first_name', None)
        last_name = validated_data.get('last_name', None)

        if first_name:
            extra_fields['first_name'] = first_name

        if last_name:
            extra_fields['last_name'] = last_name
        
        user = User.objects.create_user(validated_data['username'], validated_data['email'],
                                        validated_data['password'], **extra_fields)

        return user
    

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'first_name', 'last_name', 'email', 'email2', 'client_id',
                  'platform', 'app_uuid')

        extra_kwargs = {
            'password': {
                'write_only': True,
                'style' : {
                    'input_type': 'password',
                    'placeholder': 'Password'
                },
            },
        }



class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_('Email address'), style={'placeholder':'you@example.com'})

class LocalcosmosUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        exclude = ('password',)


'''
    The Dataset is stored using the RemoteDB interface of the webapp
    OR by using the sync button on the native app
'''


class VersionedUuidRelationField(serializers.Field):
    def __init__(self, model=None, **kwargs):
        self.model = model
        super().__init__(self, **kwargs)

    def to_representation(self, value):
        return {
            'uuid': value.uuid,
            'version': value.version
        }

    def to_internal_value(self, data):
        return self.model.objects.get(uuid=data['uuid'], version=data['version'])


class DatasetSerializer(serializers.ModelSerializer):
    assign_authenticated_user = 'user'  # assigns the authenticated user to the field user on insert and update

    created_at = serializers.DateTimeField(required=False)
    last_modified = serializers.DateTimeField(required=False)

    # SerializerMethodFields are only for to_representation
    thumbnail = serializers.SerializerMethodField()

    user = LocalcosmosUserSerializer(many=False, read_only=True)
    observation_form = VersionedUuidRelationField(source='*', model=ObservationForm)

    def get_thumbnail(self, obj):
        image = DatasetImages.objects.filter(dataset=obj).first()

        if image:
            # App clients need the full url
            relative_url = image.thumbnail(size=200)
            url = '{0}://{1}{2}'.format(self.request.scheme, self.request.get_host(), relative_url)
            return url

        return None

    class Meta:
        model = Dataset
        fields = ('__all__')
        read_only_fields = ('user_id', 'client_id')


'''
    DatasetImagesSerializer
    - keep thumbnails in sync with [App][models.js].DatasetImages.fields.image.thumbnails
'''
APP_THUMBNAILS = {
    "small": {
        "size": [100, 100],
        "type": "cover"
    },
    "medium": {
        "size": [400, 400],
        "type": "cover"
    },
    "full_hd": {
        "size": [1920, 1080],
        "type": "contain"
    }
}


class FlexImageField(serializers.ImageField):

    def to_representation(self, image):

        dataset_image = image.instance

        host = '{0}://{1}'.format(self.parent.request.scheme, self.parent.request.get_host())

        relative_url = image.url
        url = '{0}{1}'.format(host, relative_url)

        fleximage = {
            'url': url,
        }

        for name, definition in APP_THUMBNAILS.items():

            if definition['type'] == 'cover':
                relative_thumb_url = dataset_image.thumbnail(definition['size'][0])

            else:
                relative_thumb_url = dataset_image.resized(name, max_size=definition['size'])

            thumb_url = '{0}{1}'.format(host, relative_thumb_url)
            fleximage[name] = thumb_url

        return fleximage


'''
    return the DatasetImages.Dataset as a serialized Dataset
'''


class DatasetField(serializers.PrimaryKeyRelatedField):

    def to_representation(self, value):
        data = {
            'id': value.pk
        }

        return data


class DatasetImagesSerializer(serializers.ModelSerializer):
    # there is only 1 FK
    serializer_related_field = DatasetField

    class Meta:
        model = DatasetImages
        fields = ('__all__')


from django.db.models import ImageField

DatasetImagesSerializer.serializer_field_mapping[ImageField] = FlexImageField


class ObservationFormSerializer(serializers.ModelSerializer):

    class Meta:
        model = ObservationForm
        fields = ('__all__')
