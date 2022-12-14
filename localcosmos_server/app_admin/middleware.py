from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.utils.deprecation import MiddlewareMixin
from django.urls import set_urlconf

from localcosmos_server.models import App, AppUserRole

import rules


class AppAdminMiddleware(MiddlewareMixin):

    def process_view(self, request, view_func, view_args, view_kwargs):

        request.is_appadmin = False

        # the admin has to use localcosmos_server.urls to not conflict with the commercial installation
        # template_content needs the correct urlconf
        if '/app-admin/' in request.path:

            request.is_appadmin = True

            if 'app_uid' not in view_kwargs:
                raise ImproperlyConfigured('all app-admin urls require app_uid as an url kwarg')
            
            app = App.objects.get(uid=view_kwargs['app_uid'])
            request.app = app

            login_path = reverse('log_in')
            
            if login_path not in request.path:

                user = request.user
                if not user.is_authenticated:
                    url = '{0}?next={1}'.format(reverse('log_in'), request.path)
                    return redirect(url)

                has_access = rules.test_rule('app_admin.has_access', user, app)
                if not has_access:
                    raise PermissionDenied


            request.urlconf = 'localcosmos_server.urls'
            set_urlconf('localcosmos_server.urls')
        
        return None
        
