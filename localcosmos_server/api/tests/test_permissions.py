from django.test import RequestFactory, TestCase

from django.urls import reverse

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithUser, WithApp

from localcosmos_server.api.permissions import ServerContentImageOwnerOrReadOnly
from localcosmos_server.api.views import ManageServerContentImage


class TestServerContentImageOwnerOrReadOnly(WithUser, WithApp, TestCase):

    def setUp(self):
        super().setUp()
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.user = self.create_user()

    def get_url_kwargs(self, override_kwargs={}):

        url_kwargs = {
            'app_uuid' : self.app.uuid,
            'model': 'LocalcosmosUser',
            'object_id': self.user.id,
            'image_type': 'profilepicture',
        }

        url_kwargs.update(override_kwargs)

        return url_kwargs

    def get_url(self, override_kwargs={}):
        url_kwargs = self.get_url_kwargs(override_kwargs=override_kwargs)
        url = reverse('api_server_content_image', kwargs=url_kwargs)
        return url

    def get_request(self, override_kwargs={}):

        url = self.get_url(override_kwargs=override_kwargs) 
        request = self.factory.get(url)
        return request

    @test_settings
    def test_invalid_image_type(self):

        override_kwargs = {
            'image_type': 'wrongtype'
        }
        
        url = self.get_url(override_kwargs=override_kwargs)
        
        request = self.factory.get(url)
        view = ManageServerContentImage()
        view.request = request
        view.kwargs = self.get_url_kwargs(override_kwargs=override_kwargs)
        view.image_type = override_kwargs['image_type']
        

        permission = ServerContentImageOwnerOrReadOnly()

        result = permission.has_object_permission(view.request, view, self.user)

        self.assertFalse(result)


    @test_settings
    def test_get_method(self):
        
        url = self.get_url()
        
        request = self.factory.get(url)
        view = ManageServerContentImage()
        view.request = request
        view.kwargs = self.get_url_kwargs()
        view.image_type = view.kwargs['image_type']

        permission = ServerContentImageOwnerOrReadOnly()

        result = permission.has_object_permission(request, view, self.user)

        self.assertTrue(result)

    @test_settings
    def test_invalid_model_name(self):
        
        url = self.get_url()
        
        request = self.factory.get(url)
        view = ManageServerContentImage()
        view.request = request
        view.kwargs = self.get_url_kwargs()
        view.image_type = view.kwargs['image_type']
        

        permission = ServerContentImageOwnerOrReadOnly()

        result = permission.has_object_permission(view.request, view, self.app)

        self.assertFalse(result)

    @test_settings
    def test_post_valid_and_invalid(self):
        
        url = self.get_url()
        
        request = self.factory.post(url, {})
        request.user = self.user
        view = ManageServerContentImage()
        view.request = request
        view.kwargs = self.get_url_kwargs()
        view.image_type = view.kwargs['image_type']
        

        permission = ServerContentImageOwnerOrReadOnly()

        result = permission.has_object_permission(view.request, view, self.user)

        self.assertTrue(result)

        request.user = None

        result = permission.has_object_permission(view.request, view, self.user)

        self.assertFalse(result)

