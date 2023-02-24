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
'''
class LocalcosmosUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('uuid', 'username', 'first_name', 'last_name', 'email')


class RegistrationSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField()

    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField()
    email2 = serializers.EmailField()

    client_id = serializers.CharField()
    platform = serializers.CharField()

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
                  'platform')


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
