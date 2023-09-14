from rest_framework import serializers

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

from localcosmos_server.models import ServerImageStore, ServerContentImage

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import hashlib, json

class TokenObtainPairSerializerWithClientID(TokenObtainPairSerializer):

    # required for linking client_ids with users
    client_id = serializers.CharField()
    platform = serializers.CharField()

'''
    private user serializer: only accessible for the account owner
'''
class LocalcosmosUserSerializer(serializers.ModelSerializer):

    profile_picture = serializers.SerializerMethodField()

    def get_profile_picture(self, obj):
        content_image = obj.image('profilepicture')
        if content_image:

            if ('request' in self.context):
                image_url = content_image.srcset(self.context['request'])
            else:
                image_url = content_image.srcset()

            image_url = {
                'imageUrl': image_url
            }
            return image_url
        
        return None

    class Meta:
        model = User
        fields = ('id', 'uuid', 'username', 'first_name', 'last_name', 'email', 'profile_picture')


class LocalcosmosPublicUserSerializer(LocalcosmosUserSerializer):

    class Meta:
        model = User
        fields = ('uuid', 'username', 'first_name', 'last_name', 'profile_picture')


class RegistrationSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField()

    # adding those 2 lines will make these fields required for some odd reason
    #first_name = serializers.CharField(required=False)
    #last_name = serializers.CharField(required=False)
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

        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')

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


class ServerContentImageSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)

    source_image = serializers.ImageField(write_only=True) # not required for delete
    # cannot combine binary image and json field
    crop_parameters = serializers.CharField(allow_null=True, write_only=True)

    image_url = serializers.JSONField(read_only=True, source='srcset')


    def save(self, validated_data, content_instance, image_type, user, content_image=None):

        image_file = validated_data['source_image']
        content_type = ContentType.objects.get_for_model(content_instance)

        file_md5 = hashlib.md5(image_file.read()).hexdigest()
        # this line is extremely required. do not delete it. otherwise the file_ will not be read correctly
        image_file.seek(0)

        image_store = ServerImageStore(
            source_image = image_file,
            uploaded_by = user,
            md5 = file_md5,
        )

        image_store.save()

        crop_parameters = validated_data.get('crop_parameters', None)
        
        if content_image:

            content_image.image_store = image_store

            # has to be valid json
            if crop_parameters:
                content_image.crop_parameters = json.dumps(crop_parameters)
            
            content_image.save()

            new_content_image = content_image
        
        else:
            
            new_content_image = ServerContentImage(
                image_store=image_store,
                content_type=content_type,
                object_id=content_instance.id,
                image_type=image_type,
            )

            # has to be valid json
            if crop_parameters:
                new_content_image.crop_parameters = json.dumps(crop_parameters)

            new_content_image.save()

        return new_content_image

    # always return a dict
    def validate_crop_parameters(self, value):

        parsed_value = {}

        if value:
            try:
                parsed_value = json.loads(value)
                required_numbers = ['x', 'y', 'width', 'height']
                for key in required_numbers:
                    if key not in parsed_value:
                        raise serializers.ValidationError('cropParameters require {0}'.format(key))
                    else:
                        try:
                            number = int(parsed_value[key])
                        except:
                            raise serializers.ValidationError('cropParameters have to be integers'.format(key))
                    
            except:
                raise serializers.ValidationError('Invalid cropParameters')

        return parsed_value
            
