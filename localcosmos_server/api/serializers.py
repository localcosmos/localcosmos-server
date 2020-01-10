from rest_framework import serializers
from rest_framework.authtoken.models import Token

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate, get_user_model

from localcosmos_server.datasets.models import Dataset
from localcosmos_server.models import UserClients

User = get_user_model()

import uuid


'''
    AuthTokenSerializer
    - [POST] requires username or email
    - [POST] requires password, client_id and platform
    - returns a token if auth was successful
    - permissions if a user may perform an action on the tenant schema has to be done elsewhere.
      Otherwise, one could login on his on project and authenticate with this token on any other project
'''
from rest_framework.authtoken.serializers import AuthTokenSerializer
class LCAuthTokenSerializer(AuthTokenSerializer):

    # optional for linking client_ids with users
    client_id = serializers.CharField()
    platform = serializers.CharField()


    def update_datasets(self, user, client):
        # client is present now
        # update all Datasets with the user
        # this is necessary: if the user has done anonymous uploads
        client_datasets = Dataset.objects.filter(client_id=client.client_id, user__isnull=True)

        for dataset in client_datasets:
            dataset.update(user=user)
            

    # this uses email or username
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        client_id = attrs.get('client_id')
        platform = attrs.get('platform')

        if username and password and client_id and platform:

            # determine if the user exists, username can be the username or the email address
            unauthorized_user = User.objects.filter(username=username).first()

            if not unauthorized_user:
                unauthorized_user = User.objects.filter(email=username).first()

                if not unauthorized_user:
                    raise serializers.ValidationError(_('No user found for that username or email'))

                # set the correct username
                username = unathorized_user.username


            # AUTHENTICATE THE USER
            user = authenticate(request=self.context.get('request'), username=username, password=password)

            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')

            # user is authenticated now
            # one client can be used by multiple users
            # but only one client_id per browser
            # if a browser client_id exists, the user will receive it from the server
            if platform == 'browser':
                client = UserClients.objects.filter(user=user, platform='browser').first()

                if not client:
                    # create a new browser client uuid for this user
                    client_id = uuid.uuid4()

            else:
                # check if the non-browser client is linked to user
                client = UserClients.objects.filter(user=user, client_id=client_id).first()


            # if no client link is present, create one
            if not client:
                client, created = UserClients.objects.get_or_create(
                    user = user,
                    client_id = client_id,
                    platform = platform,
                )

            # update datasets
            self.update_datasets(user, client)


        else:
            msg = _('Must include "username", "password", "client_id" and "platform".')
            raise serializers.ValidationError(msg, code='authorization')


        attrs['user'] = user
        return attrs


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
    last_name = serializers.CharField(label=_('Last name (optional)'), required=False)
    email = serializers.EmailField(label=_('e-mail address'), style={'placeholder':'you@example.com'})
    email2 = serializers.EmailField(label=_('e-mail address (again)'), style={'placeholder':'you@example.com'})

    client_id = serializers.CharField(label='', style={'input_type': 'hidden',})
    platform = serializers.CharField(label='', style={'input_type': 'hidden',})

    def validate_email(self, value):
        email_exists = User.objects.filter(email__iexact=value).exists()
        if email_exists:
            raise serializers.ValidationError(_('This email address already is registered'))

        return value

    def validate(self, data):
        if data['email'] != data['email2']:
            raise serializers.ValidationError({'email2': _('The emails did not match')})

        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': _('The passwords did not match')})
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

        user_client = UserClients(
            user=user,
            platform=validated_data['platform'],
            client_id=validated_data['client_id'],
        )

        user_client.save()
        return user
    

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'first_name', 'last_name', 'email', 'email2', 'client_id',
                  'platform',)

        extra_kwargs = {
            'password': {
                'write_only': True,
                'style' : {
                    'input_type': 'password',
                    'placeholder': 'Password'
                },
            },
        }
