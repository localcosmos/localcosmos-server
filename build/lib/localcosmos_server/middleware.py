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

        if request.path_info in ['/localcosmos-setup/superuser/']:
            response = self.get_response(request)
            return response

        # check if a superuser account exists
        superuser_exists = User.objects.filter(is_superuser=True).exists()

        if not superuser_exists:
            return redirect(reverse('localcosmos_setup_superuser'))


        response = self.get_response(request)
        return response
        
