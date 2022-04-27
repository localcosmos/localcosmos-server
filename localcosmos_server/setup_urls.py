from django.urls import  path

from . import views
from . import setup_views

urlpatterns = [
    path('localcosmos-setup/superuser/', setup_views.SetupSuperUser.as_view(), name='localcosmos_setup_superuser'),
]
