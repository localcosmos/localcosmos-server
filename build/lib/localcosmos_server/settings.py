'''
    LOCALCOSMOS SERVER DJANGO SETTINGS
'''
from django.utils.translation import ugettext_lazy as _


SITE_ID = 1

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'


AUTHENTICATION_BACKENDS = (
        'rules.permissions.ObjectPermissionBackend',
        'django.contrib.auth.backends.ModelBackend',
)

LOGOUT_REDIRECT_URL = '/server/loggedout/'


# this setting is used in localcosmos_server.models.App
LOCALCOSMOS_OPEN_SOURCE = True

# USER MODEL
AUTH_USER_MODEL = 'localcosmos_server.LocalcosmosUser'

# ROAD
ROAD_MODEL_PERMISSIONS = 'localcosmos_server.api.road_permissions.ROAD_MODEL_PERMISSIONS'
ROAD_MODEL_SERIALIZERS = 'localcosmos_server.api.road_serializers'

ANYCLUSTER_GEODJANGO_MODEL = 'datasets.Dataset'
ANYCLUSTER_COORDINATES_COLUMN = 'coordinates'
ANYCLUSTER_COORDINATES_COLUMN_SRID = 3857
ANYCLUSTER_PINCOLUMN = 'taxon_nuid'
ANYCLUSTER_ADDITIONAL_COLUMN = 'taxon_source'

# make session available for apps
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = None


# corsheaders
# the api has to allow queries from everywhere
CORS_ORIGIN_ALLOW_ALL = True
# but only allow querying the api
CORS_URLS_REGEX = r'^/api/.*$'
# needed for anycluster cache
CORS_ALLOW_CREDENTIALS = True

# django_rest_framework
# enable token authentication only for API
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'localcosmos_server.api.authentication.LCTokenAuthentication',
    ),
    #'DEFAULT_FILTER_BACKENDS': (
    #    'rest_framework.filters.DjangoFilterBackend',
    #),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,
}


DATASET_VALIDATION_CLASSES = (
    #'localcosmos_server.datasets.validation.ReferenceFieldsValidator', # unfinished
    'localcosmos_server.datasets.validation.ExpertReviewValidator',
)

LOCALCOSMOS_ENABLE_GOOGLE_CLOUD_API = False

LOGIN_REDIRECT_URL = '/server/control-panel/'
