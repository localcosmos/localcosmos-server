'''
    LOCALCOSMOS SERVER DJANGO SETTINGS
'''
from datetime import timedelta

from django.utils.translation import gettext_lazy as _


SITE_ID = 1

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

AUTHENTICATION_BACKENDS = (
    'rules.permissions.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)

LOGOUT_REDIRECT_URL = '/server/loggedout/'


# this setting is used in localcosmos_server.models.App
LOCALCOSMOS_PRIVATE = True

# USER MODEL
AUTH_USER_MODEL = 'localcosmos_server.LocalcosmosUser'

ANYCLUSTER_GEODJANGO_MODEL = 'datasets.Dataset'
ANYCLUSTER_COORDINATES_COLUMN = 'coordinates'
ANYCLUSTER_COORDINATES_COLUMN_SRID = 3857
ANYCLUSTER_PINCOLUMN = 'taxon_nuid'
ANYCLUSTER_ADDITIONAL_COLUMN = 'taxon_source'
ANYCLUSTER_FILTERS = ['taxon_nuid', 'taxon_source', 'observation_form_id']
ANYCLUSTER_GIS_MODEL_SERIALIZER = 'localcosmos_server.datasets.api.serializers.DatasetRetrieveSerializer'
ANYCLUSTER_ADDITIONAL_GROUP_BY_COLUMNS = ['taxon_source', 'taxon_latname', 'taxon_author', 'taxon_nuid']

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

# needed for anycluster cache to work wit apps/cordova
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'

# django_rest_framework
# enable token authentication only for API
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    #'DEFAULT_FILTER_BACKENDS': (
    #    'rest_framework.filters.DjangoFilterBackend',
    #),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
        # Any other renders
    ),

    'DEFAULT_PARSER_CLASSES': (
        # If you use MultiPartFormParser or FormParser, we also have a camel case version
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        # Any other parsers
    ),
    'JSON_UNDERSCOREIZE': {
        'no_underscore_before_number': True,
        'ignore_fields': ('data', 'definition', 'image'),
    },
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'Local Cosmos Server API',
    'DESCRIPTION': 'API Documentation for the Local Cosmos Server',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'PREPROCESSING_HOOKS': ['localcosmos_server.utils.api_filter_endpoints_hook'],
    'POSTPROCESSING_HOOKS':['drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields']
}


DATASET_VALIDATION_CLASSES = (
    #'localcosmos_server.datasets.validation.ReferenceFieldsValidator', # unfinished
    'localcosmos_server.datasets.validation.ExpertReviewValidator',
)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(weeks=13),
    'REFRESH_TOKEN_LIFETIME': timedelta(weeks=26),
}

LOCALCOSMOS_ENABLE_GOOGLE_CLOUD_API = False

LOGIN_REDIRECT_URL = '/server/control-panel/'


LOCALCOSMOS_SERVER_PUBLISH_INVALID_DATA = True

# temporary el_pagination fix
import django
from django.utils.encoding import force_str
django.utils.encoding.force_text = force_str