from django.test import TestCase
from django import forms

from localcosmos_server.forms import (LocalizeableForm, LocalizeableModelForm, EmailOrUsernameAuthenticationForm,
                                      ManageContentImageFormCommon)

from localcosmos_server.models import LocalcosmosUser

from content_licencing.mixins import LicencingFormMixin

from .mixins import WithUser, WithImageForForm
from .common import powersetdic

import json, hashlib


class FormForTest(LocalizeableForm):

    localizeable_field = forms.CharField()
    regular_field = forms.CharField()

    localizeable_fields = ['localizeable_field']


class FormTestCommon:

    def test_with_language(self):

        language = 'en'

        kwargs = {
            'language' : language
        }

        form = self.form_class(**kwargs)

        self.assertEqual(form.fields['input_language'].initial, language)
        self.assertEqual(form.fields['localizeable_field'].language, language)
        self.assertFalse(hasattr(form.fields['regular_field'], 'language'))


    def test_without_language(self):

        language = None

        form = self.form_class()

        self.assertEqual(form.fields['input_language'].initial, language)
        self.assertEqual(form.fields['localizeable_field'].language, language)
        self.assertFalse(hasattr(form.fields['regular_field'], 'language'))


class TestLocalizeableForm(FormTestCommon, TestCase):
        
    form_class = FormForTest
    
        

class ModelFormForTest(LocalizeableModelForm):

    localizeable_field = forms.CharField()
    regular_field = forms.CharField()

    localizeable_fields = ['localizeable_field']

    class Meta:
        model = LocalcosmosUser
        fields = '__all__'


    
class TestLocalizeableModelForm(FormTestCommon, TestCase):

    form_class = ModelFormForTest


class TestEmailOrUsernameAuthenticationForm(WithUser, TestCase):

    def setUp(self):
        self.user = self.create_user()

    def test_clean(self):

        data = {}

        form = EmailOrUsernameAuthenticationForm(data=data)
        self.assertFalse(form.is_valid())

        # test wrong pw and correct username
        data = {
            'username': self.test_username,
            'password' : 'wrong',
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertFalse(form.is_valid())

        with self.assertRaises(forms.ValidationError):
            cleaned_data = form.clean()

        # test wrong pw and correct email
        data = {
            'username' : self.test_email,
            'password' : 'wrong',
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertFalse(form.is_valid())

        with self.assertRaises(forms.ValidationError):
            cleaned_data = form.clean()


        # test wrong pw and wrong email
        data = {
            'username' : 'wrong@email.com',
            'password' : 'wrong',
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertFalse(form.is_valid())

        with self.assertRaises(forms.ValidationError):
            cleaned_data = form.clean()


        # test wrong pw and wrong username
        data = {
            'username' : 'wrong_user',
            'password' : 'wrong',
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertFalse(form.is_valid())

        with self.assertRaises(forms.ValidationError):
            cleaned_data = form.clean()


        # test correct credentials, username
        self.assertTrue(self.user.is_active)
        data = {
            'username' : self.test_username,
            'password' : self.test_password,
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertTrue(form.is_valid())

        
        # test correct credentials, email
        data = {
            'username' : self.test_email,
            'password' : self.test_password,
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertTrue(form.is_valid())


        # test inactive user
        self.user.is_active = False
        self.user.save()

        data = {
            'username' : self.test_email,
            'password' : self.test_password,
        }

        form = EmailOrUsernameAuthenticationForm(data=data)

        self.assertFalse(form.is_valid())

        
class FormForImageFormTest(ManageContentImageFormCommon, LicencingFormMixin, forms.Form):

    # these fields are optional and not all subclasses have them
    # adding them here is necessary to test the field ordering
    crop_parameters = forms.CharField(required=False)
    image_type = forms.CharField(required=False)
    md5 = forms.CharField(required=False)
    

class TestManageContentImageFormCommon(WithImageForForm, TestCase):


    def test__init__(self):

        form = FormForImageFormTest()

        field_order = ['source_image', 'image_type', 'crop_parameters', 'md5', 'creator_name', 'creator_link',
            'source_link', 'licence',]

        
        for counter, field in enumerate(form, 0):
            self.assertEqual(counter, field_order.index(field.name))

        self.assertEqual(form.current_image, None)

        # current image
        current_image = 'path/to/image.jpg'
        form = FormForImageFormTest(current_image=current_image)

        self.assertEqual(form.current_image, current_image)


    def test_get_source_image(self):
        
        form = FormForImageFormTest()

        source_image_field = form.get_source_image_field()
        self.assertFalse(source_image_field.required)
        self.assertTrue(isinstance(source_image_field, forms.ImageField))
        self.assertEqual(source_image_field.widget.current_image, None)


        current_image = 'path/to/image.jpg'
        form = FormForImageFormTest(current_image=current_image)
        source_image_field = form.get_source_image_field()
        self.assertEqual(source_image_field.widget.current_image, current_image)


    def test_clean_crop_parameters(self):

        wrong_crop_parameters = {
            'a' : 1,
            'b' : 2,
        }

        data = {
            'crop_parameters' : json.dumps(wrong_crop_parameters)
        }
        
        form = FormForImageFormTest(data=data)
        form.cleaned_data = data

        with self.assertRaises(forms.ValidationError):
            crop_parameters = form.clean_crop_parameters()


        # width and height 0
        wrong_crop_parameters_2 = {
            'width' : 0,
            'height' : 0,
        }

        data_2 = {
            'crop_parameters' : json.dumps(wrong_crop_parameters_2)
        }

        form = FormForImageFormTest(data=data_2)
        form.cleaned_data = data_2

        with self.assertRaises(forms.ValidationError):
            crop_parameters = form.clean_crop_parameters()


        # valid clean with no crop parameters
        empty_data = {}

        form = FormForImageFormTest(data=empty_data)
        form.cleaned_data = empty_data
        cleaned_crop_parameters = form.clean_crop_parameters()
        self.assertEqual(cleaned_crop_parameters, None)

        # valid form with valid crop parameters
        valid_data = {
            'width' : 12,
            'height' : 20,
        }

        form = FormForImageFormTest(data=valid_data)
        form.cleaned_data = valid_data
        cleaned_crop_parameters = form.clean_crop_parameters()
        self.assertEqual(cleaned_crop_parameters, None)


    def test_clean(self):

        data = {
            'creator_name' : 'Test name',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
        }

        image = self.get_image('test-image.jpg')
        
        file_dict = {
            'source_image': image
        }

        form = FormForImageFormTest(data=data, files=file_dict)

        self.assertTrue(form.is_valid())


    def test_clean_correct_md5(self):

        image = self.get_image('test-image.jpg')
        correct_md5 = hashlib.md5(image.read()).hexdigest()

        image = self.get_image('test-image.jpg')

        file_dict = {
            'source_image': image
        }

        data = {
            'creator_name' : 'Test name',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'md5' : correct_md5,
        }
        
        form = FormForImageFormTest(data=data, files=file_dict)

        self.assertTrue(form.is_valid())


    def test_clean_incorrect_md5(self):

        image = self.get_image('test-image.jpg')
        incorrect_md5 = 'abcdef'

        file_dict = {
            'source_image': image
        }

        data = {
            'creator_name' : 'Test name',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'md5' : incorrect_md5,
        }
        
        form = FormForImageFormTest(data=data, files=file_dict)

        self.assertFalse(form.is_valid())


        

        


        
