from django.test import TestCase

from localcosmos_server.tests.common import test_settings, TEST_CLIENT_ID, TEST_PLATFORM
from localcosmos_server.tests.mixins import WithUser

from localcosmos_server.api.serializers import (TokenObtainPairSerializerWithClientID, RegistrationSerializer,
    PasswordResetSerializer)


from rest_framework import serializers


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

