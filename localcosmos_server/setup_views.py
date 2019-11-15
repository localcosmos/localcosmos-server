from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.sites.models import Site

from .utils import get_domain_name


from .setup_forms import SetupSuperuserForm


User = get_user_model()

# if someone installs localcosmos, we need to redirect somewhere after installation
SUCCESS_REDIRECT = 'scp:home'

class SetupSuperUser(FormView):
    template_name = 'localcosmos_server/setup/setup_superuser.html'
    form_class = SetupSuperuserForm

    def dispatch(self, request, *args, **kwargs):

        site = Site.objects.get(pk=settings.SITE_ID)
        domain_name = get_domain_name(request)

        if domain_name != site.domain:
            site.domain = domain_name
            site.name = domain_name
            site.save()
        
        if User.objects.filter(is_superuser=True).exists():
            return redirect(reverse(SUCCESS_REDIRECT))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        admin = form.save()
        
        return redirect(reverse(SUCCESS_REDIRECT))





