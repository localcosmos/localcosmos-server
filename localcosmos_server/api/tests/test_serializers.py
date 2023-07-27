from django.test import TestCase

from django.core.files.uploadedfile import SimpleUploadedFile

from localcosmos_server.tests.common import test_settings, TEST_CLIENT_ID, TEST_PLATFORM, TEST_IMAGE_PATH
from localcosmos_server.tests.mixins import WithUser, WithMedia, WithServerContentImage

from localcosmos_server.api.serializers import (TokenObtainPairSerializerWithClientID, RegistrationSerializer,
    PasswordResetSerializer, ServerContentImageSerializer)


from rest_framework import serializers

import json


class TestTokenObtainPairSerializerWithClientId(WithUser, TestCase):

    @test_settings
    def test_serialize(self):
        
        user = self.create_user()

        data = {
            'username': self.test_username,
            'password': self.test_password,
            'client_id': TEST_CLIENT_ID,
            'platform': TEST_PLATFORM,
        }

        serializer = TokenObtainPairSerializerWithClientID(data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})


class TestRegistrationSerializer(WithUser, TestCase):


    def get_data(self):

        data = {
            'username': self.test_username,
            'password': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
            'email': self.test_email,
            'email2': self.test_email,
            'client_id': TEST_CLIENT_ID,
            'platform': TEST_PLATFORM,
        }

        return data


    @test_settings
    def test_serialize(self):

        data = self.get_data()

        serializer = RegistrationSerializer(data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})


    @test_settings
    def test_validate_email(self):
        
        user = self.create_user()

        data = self.get_data()

        serializer = RegistrationSerializer(data=data)

        with self.assertRaises(serializers.ValidationError):   
            value = serializer.validate_email(self.test_email)

        alt_email = 'another@mail.com'

        value = serializer.validate_email(alt_email)

        self.assertEqual(value, alt_email)
        

    @test_settings
    def test_validate(self):
        
        data = self.get_data()

        data['password2'] = 'another pw'

        serializer = RegistrationSerializer(data=data)

        with self.assertRaises(serializers.ValidationError):   
            data2 = serializer.validate(data)

        data = self.get_data()

        data['email2'] = 'another@mail.com'

        serializer = RegistrationSerializer(data=data)

        with self.assertRaises(serializers.ValidationError):   
            data2 = serializer.validate(data)


    @test_settings
    def test_create(self):
        
        data = self.get_data()

        serializer = RegistrationSerializer(data=data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        user = serializer.create(serializer.validated_data)

        for key in ['username', 'email', 'first_name', 'last_name']:
            self.assertEqual(data[key], getattr(user, key))


class TestServerContentImageSerializer(WithUser, WithServerContentImage, WithMedia, TestCase):

    def get_crop_parameters(self):
        crop_parameters = {
            'x': 1,
            'y': 2,
            'width': 3,
            'height': 4,
        }

        return crop_parameters 

    def get_data(self, override_data={}):

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')
        data = {
            'source_image' : image,
            'crop_parameters' : None,
        }

        data.update(override_data)

        return data
    
    @test_settings
    def test_serialize(self):

        self.user = self.create_user()

        image_type = 'profilepicture'

        profile_picture = self.get_content_image(self.user, self.user, image_type=image_type)

        serializer = ServerContentImageSerializer(profile_picture)

        media_path = '/media/localcosmos-server/imagestore/{0}/thumbnails/a6a11b61d65ee19c4c22caa0682288ff-uncropped-nofeatures-'.format(self.user.id)

        expected_data = {
            'id': profile_picture.id,
            'image_url': {
                '1x': '{0}200.jpg'.format(media_path),
                '2x': '{0}400.jpg'.format(media_path)
            }
        }

        for key, value in expected_data.items():
            self.assertEqual(value, serializer.data[key])

        self.assertEqual(serializer.data, expected_data)

        profile_picture.crop_parameters = json.dumps(self.get_crop_parameters())
        profile_picture.save()

        serializer = ServerContentImageSerializer(profile_picture)

        cropped_media_path = '/media/localcosmos-server/imagestore/{0}/thumbnails/a6a11b61d65ee19c4c22caa0682288ff-dffbde21fc7c45cf16aa73eddcf7f8cd-nofeatures-'.format(self.user.id)

        cropped_expected_data = {
            'id': profile_picture.id,
            'image_url': {
                '1x': '{0}200.jpg'.format(cropped_media_path),
                '2x': '{0}400.jpg'.format(cropped_media_path)
            }
        }

        for key, value in cropped_expected_data.items():
            self.assertEqual(value, serializer.data[key])

        self.assertEqual(serializer.data, cropped_expected_data)


    @test_settings
    def test_deserialize(self):

        self.user = self.create_user()
        
        data = self.get_data()
        serializer = ServerContentImageSerializer(data=data)
        serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        expected_data = data.copy()
        expected_data.update({
            'crop_parameters': {}
        })

        self.assertEqual(dict(serializer.validated_data), expected_data)

    @test_settings
    def test_deserialize_with_crop_parameters(self):

        self.user = self.create_user()
        
        override_data = {
            'crop_parameters' : self.get_crop_parameters()
        }
        data = self.get_data(override_data=override_data)
        serializer = ServerContentImageSerializer(data=data)
        serializer.is_valid()

        self.assertIn('crop_parameters', serializer.errors)


        override_data = {
            'crop_parameters' : json.dumps(self.get_crop_parameters())
        }
        data = self.get_data(override_data=override_data)
        serializer = ServerContentImageSerializer(data=data)
        serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        expected_data = data.copy()
        expected_data.update({
            'crop_parameters': self.get_crop_parameters()
        })

        self.assertEqual(dict(serializer.validated_data), expected_data)



