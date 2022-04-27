from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

from django.core.exceptions import PermissionDenied

User = get_user_model()

'''
    Check if everything is set up correctly
'''
class LocalCosmosServerSetupMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        localcosmos_create_superuser_url = reverse('localcosmos_setup_superuser')

        if request.path_info in [localcosmos_create_superuser_url]:
            response = self.get_response(request)
            return response

        # check if a superuser account exists
        superuser_exists = User.objects.filter(is_superuser=True).exists()

        if not superuser_exists:
            return redirect(localcosmos_create_superuser_url)


        response = self.get_response(request)
        return response
        
