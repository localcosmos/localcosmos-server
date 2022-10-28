from rest_framework import serializers

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
