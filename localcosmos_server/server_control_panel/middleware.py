from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

from django.core.exceptions import PermissionDenied

User = get_user_model()

'''
    Check if everything is set up correctly
'''
class ServerControlPanelMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if 'server/control-panel' in request.path_info:

            if request.user.is_authenticated:
                if not request.user.is_superuser:
                    raise PermissionDenied

            else:

                login_path = reverse('log_in')

                if login_path not in request.path:                
                    url = '{0}?next={1}'.format(reverse('log_in'), request.path)
                    return redirect(url)
        
        response = self.get_response(request)
        return response
        
