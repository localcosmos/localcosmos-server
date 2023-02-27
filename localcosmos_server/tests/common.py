from django.test import TestCase, override_settings
import os

from localcosmos_server.utils import timestamp_from_utc_with_offset

TESTS_ROOT = os.path.dirname(os.path.realpath(__file__))
TEST_DATA_ROOT = os.path.join(TESTS_ROOT, 'data_for_tests')
TEST_OBSERVATION_FORM_JSON = os.path.join(TEST_DATA_ROOT, 'observation_form.json')
TEST_OBSERVATION_FORM_POINT_JSON = os.path.join(TEST_DATA_ROOT, 'observation_form_point.json')
TEST_APPS_ROOT = os.path.join(TESTS_ROOT, 'apps')


TESTAPP_NAO_UID = 'app_no_anonymous_observations'
TESTAPP_AO_UID = 'app_anonymous_observations'

TESTAPP_NAO_RELATIVE_PATH = '{0}/release/sources/www/'.format(TESTAPP_NAO_UID)
TESTAPP_AO_RELATIVE_PATH = '{0}/release/sources/www/'.format(TESTAPP_AO_UID)

TESTAPP_NAO_PREVIEW_RELATIVE_PATH = '{0}/preview/sources/www/'.format(TESTAPP_NAO_UID)
TESTAPP_AO_PREVIEW_RELATIVE_PATH = '{0}/preview/sources/www/'.format(TESTAPP_AO_UID)

TESTAPP_NAO_ABSOLUTE_PATH = os.path.join(TEST_APPS_ROOT, TESTAPP_NAO_RELATIVE_PATH)
TESTAPP_AO_ABSOLUTE_PATH = os.path.join(TEST_APPS_ROOT, TESTAPP_AO_RELATIVE_PATH)

TEST_IMAGE_PATH = os.path.join(TESTS_ROOT, 'images', 'Leaf.jpg')

LARGE_TEST_IMAGE_PATH = os.path.join(TESTS_ROOT, 'images', 'test-image-2560-1440.jpg')

TEST_MEDIA_ROOT = os.path.join(TESTS_ROOT, 'media_for_tests')

test_settings = override_settings(
    LOCALCOSMOS_PRIVATE = True,
    LOCALCOSMOS_APPS_ROOT = TEST_APPS_ROOT,
    MEDIA_ROOT = TEST_MEDIA_ROOT,
    DATASET_VALIDATION_CLASSES = (
        'localcosmos_server.datasets.validation.ExpertReviewValidator',
        'localcosmos_server.datasets.validation.ReferenceFieldsValidator',
    ),
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend',
)

test_settings_commercial = override_settings(
    LOCALCOSMOS_PRIVATE = False,
    LOCALCOSMOS_APPS_ROOT = TEST_APPS_ROOT,
    MEDIA_ROOT = TEST_MEDIA_ROOT,
)

TEST_CLIENT_ID = '4cf82a1d-755b-49e5-b687-a38d78591df4'
TEST_PLATFORM = 'browser'
TEST_UTC_TIMESTAMP = 1576161098595
TEST_TIMESTAMP_OFFSET = -60

TEST_TIMESTAMP = timestamp_from_utc_with_offset(TEST_UTC_TIMESTAMP, TEST_TIMESTAMP_OFFSET)

TEST_LATITUDE = 49.63497717058325
TEST_LONGITUDE = 11.091344909741967

GEOJSON_POLYGON = {
    "type": "Feature",
    "geometry": {
        "crs": {
            "type": "name",
            "properties": {
                "name": "EPSG:4326"
            }
        },
        "type": "Polygon",
        "coordinates": [
            [
                [100.0, 0.0],
                [101.0, 0.0],
                [101.0, 1.0],
                [100.0, 1.0],
                [100.0, 0.0]
            ]
        ]
    }
}


TEST_USER_GEOMETRY_NAME = 'Test user geometry'



class DataCreator:

    def get_dataset_data(self, observation_form_json, alternative_data=False):
        
        data = {}

        # iterate over all fields of observation_form_json and create test data
        for field in observation_form_json['fields']:
            
            method_name = 'get_{0}_test_data'.format(field['fieldClass'])
            field_data = getattr(self, method_name)(field, alternative_data)
            data[field['uuid']] = field_data

        return data


    def get_TaxonField_test_data(self, field, alternative_data=False):

        data = {
            "taxonNuid": "006002009001005007001",
            "nameUuid": "1541aa08-7c23-4de0-9898-80d87e9227b3",
            "taxonSource": "taxonomy.sources.col",
            "taxonLatname": "Picea abies",
            "taxonAuthor":"Linnaeus"
        }

        return data

    def get_PointJSONField_test_data(self, field, alternative_data=False):

        data = {
            "type": "Feature",
            "geometry": {
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "EPSG:4326"
                    }
                },
                "type": "Point",
                "coordinates": [TEST_LONGITUDE, TEST_LATITUDE]
            },
            "properties": {
                "accuracy": 1
            }
        }

        return data

    # use a polygon
    def get_GeoJSONField_test_data(self, field, alternative_data=False):

        data = {
            "type": "Feature",
            "geometry": {
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "EPSG:4326"
                    }
                },
                "type": "Polygon",
                "coordinates": [
                    [
                        [100.0, 0.0],
                        [101.0, 0.0],
                        [101.0, 1.0],
                        [100.0, 1.0],
                        [100.0, 0.0]
                    ]
                ]
            },
            "properties": {}
        }

        return data

    def get_DateTimeJSONField_test_data(self, field, alternative_data=False):

        data = {
            "cron": {
                "type": "timestamp",
                "format": "unixtime",
                "timestamp": TEST_UTC_TIMESTAMP,
                "timezoneOffset": TEST_TIMESTAMP_OFFSET
            },
            "type": "Temporal"
        }

        return data


    def get_BooleanField_test_data(self, field, alternative_data=False):
        return True

    def get_CharField_test_data(self, field, alternative_data=False):
        data = 'CharField Content'

        if alternative_data:
            data = 'CharField alternative Content'

        return data

    def get_DecimalField_test_data(self, field, alternative_data=False):
        return 1.12

    def get_FloatField_test_data(self, field, alternative_data=False):
        return 2.34

    def get_IntegerField_test_data(self, field, alternative_data=False):
        return 7

    def get_ChoiceField_test_data(self, field, alternative_data=False):
        return field['definition']['choices'][-1][0]

    def get_MultipleChoiceField_test_data(self, field, alternative_data=False):
        
        choices = field['definition']['choices']

        data = [choices[-1][0], choices[-2][0]]
        return data

    def get_PictureField_test_data(self, field, alternative_data=False):
        return None
        

# create a set of all possible subdics
def powersetdic(d):

    keys = list(d.keys())

    r = [[]]
    rd = [{}]
    
    for e in keys:
        r += [ls+[e] for ls in r]

    for b in r:
    
        if len(b) > 0:
            subdic = {}
            for key in b:
                subdic[key] = d[key]

            rd.append(subdic)

    return rd


class MockPost:

    def __init__(self, data):
        self.data = data

    def getlist(self, name, *args, **kwargs):
        return self.data[name]


    def get(self, key, default=None):
        """
        Return the last data value for the passed key. If key doesn't exist
        or value is an empty list, return `default`.
        """
        try:
            val = self.data[key]
        except KeyError:
            return default
        if val == []:
            return default
        return val
