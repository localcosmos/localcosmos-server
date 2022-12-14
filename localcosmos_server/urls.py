from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('server/', include('localcosmos_server.global_urls')),
    
    # APP ADMIN
    path('app-admin/', include('localcosmos_server.app_admin.urls', namespace='appadmin')),
    path('app-admin/', include('localcosmos_server.template_content.urls')), # cannot have the namespace appadmin
    path('app-admin/', include('localcosmos_server.datasets.urls', namespace='datasets')), # cannot have the namespace appadmin
    path('app-admin/', include('localcosmos_server.taxonomy.urls')), # cannot have the namespace appadmin
    # API
    path('api/', include('django_road.urls')),
    path('api/', include('localcosmos_server.api.urls')),
    path('api/', include('localcosmos_server.template_content.api.urls')),
    path('api/anycluster/', include('localcosmos_server.anycluster_schema_urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(template_name='swagger-ui.html', url_name='schema'), name='swagger-ui'),
]

if getattr(settings, 'LOCALCOSMOS_ENABLE_GOOGLE_CLOUD_API', False) == True:
    urlpatterns += [path('api/google-cloud/', include('localcosmos_server.google_cloud_api.urls')),]
