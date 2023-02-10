from django.test import TestCase, override_settings
import os

TESTS_ROOT = os.path.dirname(os.path.realpath(__file__))
TEST_DATA_ROOT = os.path.join(TESTS_ROOT, 'data_for_tests')
TEST_OBSERVATION_FORM_JSON = os.path.join(TEST_DATA_ROOT, 'observation_form.json')
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



TEST_CLIENT_ID = "4cf82a1d-755b-49e5-b687-a38d78591df4"
TEST_UTC_TIMESTAMP = 1576161098595
TEST_TIMESTAMP_OFFSET = -60

TEST_LATITUDE = 49.63497717058325
TEST_LONGITUDE = 11.091344909741967



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
        },

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
                "timezone_offset": TEST_TIMESTAMP_OFFSET
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

'''
TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS = {
    "type": "Dataset",
    "dataset": {
        "type": "Observation",
        "properties": {},
        "reported_values": {
            "client_id": TEST_CLIENT_ID,
            "platform": "browser",
            "0f444e85-e31d-443d-afd3-2fa35df08ce3": {"cron": {"type": "timestamp", "format": "unixtime", "timestamp": TEST_UTC_TIMESTAMP, "timezone_offset": TEST_TIMESTAMP_OFFSET}, "type": "Temporal"},
            "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce": {
                
            },
            "96e8ff3b-ffcc-4ccd-b81c-542f37ce53d0": None,
            "a4d53718-715f-4436-9b4c-09fce7978153": {"type": "Feature", "geometry": {"crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "type": "Point", "coordinates": [TEST_LONGITUDE, TEST_LATITUDE]}, "properties": {"accuracy": 1}}
        },
        "observation_form": {
            "name": "Baumbeobachtung",
            "uuid": "c07271c1-3d36-430c-aa4d-bfbb8cb279fa",
            "fields": [
                {"role": "taxonomic_reference", "uuid": "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce", "options": {}, "version": 1, "position": -3, "definition": {"label": "Baumart", "widget": "BackboneTaxonAutocompleteWidget", "initial": None, "required": True, "help_text": None, "is_sticky": False}, "field_class": "TaxonField", "widget_attrs": {}, "taxonomic_restriction": []},
                {"role": "geographic_reference", "uuid": "a4d53718-715f-4436-9b4c-09fce7978153", "options": {}, "version": 1, "position": -2, "definition": {"label": "Ort", "widget": "MobilePositionInput", "initial": None, "required": True, "help_text": None, "is_sticky": False}, "field_class": "PointJSONField", "widget_attrs": {}, "taxonomic_restriction": []},
                {"role": "temporal_reference", "uuid": "0f444e85-e31d-443d-afd3-2fa35df08ce3", "options": {}, "version": 1, "position": -1, "definition": {"label": "Zeitpunkt", "widget": "SelectDateTimeWidget", "initial": None, "required": True, "help_text": None, "is_sticky": False}, "field_class": "DateTimeJSONField", "widget_attrs": {}, "taxonomic_restriction": []},
                {"role": "regular", "uuid": "96e8ff3b-ffcc-4ccd-b81c-542f37ce53d0", "options": {}, "version": 1, "position": 4, "definition": {"label": "Eichenprozessionsspinner", "widget": "CheckboxInput", "initial": None, "required": False, "help_text": None, "is_sticky": False}, "field_class": "BooleanField", "widget_attrs": {}, "taxonomic_restriction": [{"taxon_nuid": "00600200700q003007", "name_uuid": "99000227-c450-4eb4-a6e4-e974d587cdd8", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Quercus", "restriction_type": "exists"}]},
                {"role": "regular", "uuid": "85e8e05c-5a60-46f8-b49c-b6debbe19997", "options": {}, "version": 1, "position": 5, "definition": {"label": "Bilder", "widget": "CameraAndAlbumWidget", "initial": None, "required": False, "help_text": None, "is_sticky": False}, "field_class": "PictureField", "widget_attrs": {}, "taxonomic_restriction": []}
            ],
            "options": {},
            "version": 2,
            "global_options": {},
            "temporal_reference": "0f444e85-e31d-443d-afd3-2fa35df08ce3",
            "taxonomic_reference": "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce",
            "geographic_reference": "a4d53718-715f-4436-9b4c-09fce7978153",
            "taxonomic_restriction": []
        },
        "specification_version": 1
    },
    "properties": {"thumbnail": {"url": None}}
}

TEST_DATASET_FULL_GENERIC_FORM = {
    "type" : "Dataset",
    "dataset" : {
        "type" : "Observation",
        "properties" : {},
        "reported_values" : {
            "client_id": TEST_CLIENT_ID,
            "platform": "browser",
            "33cf1019-c8a1-4091-8c23-c95489c39094": {"cron": {"type": "timestamp", "format": "unixtime", "timestamp": TEST_UTC_TIMESTAMP, "timezone_offset": TEST_TIMESTAMP_OFFSET}, "type": "Temporal"},
            "7dfd9ff4-456e-426d-9772-df5824dab18f": {"taxon_nuid": "006002009001005007001", "name_uuid": "1541aa08-7c23-4de0-9898-80d87e9227b3", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Picea abies", "taxon_author":"Linnaeus"},
            "98332a11-d56e-4a92-aeda-13e2f74453cb": {"type": "Feature", "geometry": {"crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "type": "Point", "coordinates": [TEST_LONGITUDE, TEST_LATITUDE]}, "properties": {"accuracy": 1}},
            "25efa219-c631-4701-98ed-d007f1acf3de" : "test text",
            "4b62fae2-0e6f-49e5-87a5-6a0756449273" : 1,
            "b4b153d3-7b9b-4a32-b5b1-6ec3e95b6ec7" : -1.1,
            "969d04d9-cbc2-45d1-83cd-1d3450fe8a35" : 4,
            
            
        },
        "observation_form" : {
            "uuid": "b5769696-f550-4fdb-8aea-95845d853764",
            "version": 1,
            "options": {},
            "global_options": {},
            "name": "Test Observation Form",
            "fields": [
                {"uuid": "7dfd9ff4-456e-426d-9772-df5824dab18f", "field_class": "TaxonField", "version": 1, "role": "taxonomic_reference", "definition": {"widget": "BackboneTaxonAutocompleteWidget", "required": True, "is_sticky": False, "label": "Taxon Field", "help_text": None, "initial": None}, "position": -3, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "98332a11-d56e-4a92-aeda-13e2f74453cb", "field_class": "PointJSONField", "version": 2, "role": "geographic_reference", "definition": {"widget": "MobilePositionInput", "required": True, "is_sticky": False, "label": "Ort", "help_text": None, "initial": None}, "position": -2, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "33cf1019-c8a1-4091-8c23-c95489c39094", "field_class": "DateTimeJSONField", "version": 2, "role": "temporal_reference", "definition": {"widget": "SelectDateTimeWidget", "required": True, "is_sticky": False, "label": "Zeitpunkt", "help_text": None, "initial": None}, "position": -1, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "e46c1a77-2070-49b4-a027-ca6b345cdca3", "field_class": "BooleanField", "version": 1, "role": "regular", "definition": {"widget": "CheckboxInput", "required": False, "is_sticky": False, "label": "Checkbox", "help_text": None, "initial": None}, "position": 4, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "25efa219-c631-4701-98ed-d007f1acf3de", "field_class": "CharField", "version": 1, "role": "regular", "definition": {"widget": "TextInput", "required": False, "is_sticky": False, "label": "Text", "help_text": None, "initial": None}, "position": 5, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "3f96ddc1-1d1b-4a52-a24c-b94d3e063923", "field_class": "ChoiceField", "version": 1, "role": "regular", "definition": {"widget": "Select", "required": False, "is_sticky": False, "label": "Dropdown", "help_text": None, "initial": None, "choices": [["", "-----"], ["choice 2", "choice 2"], ["choice 1", "choice 1"]]}, "position": 6, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "4b62fae2-0e6f-49e5-87a5-6a0756449273", "field_class": "DecimalField", "version": 1, "role": "regular", "definition": {"widget": "MobileNumberInput", "required": False, "is_sticky": False, "label": "Decimal", "help_text": None, "initial": None}, "position": 7, "options": {"step": 0.5, "max_value": 10.0, "decimal_places": 1}, "widget_attrs": {"max": 10.0, "step": "0.1"}, "taxonomic_restriction": []},
                {"uuid": "b4b153d3-7b9b-4a32-b5b1-6ec3e95b6ec7", "field_class": "FloatField", "version": 1, "role": "regular", "definition": {"widget": "MobileNumberInput", "required": False, "is_sticky": False, "label": "Float", "help_text": None, "initial": None}, "position": 8, "options": {"step": 0.1, "max_value": 5.0, "min_value": -5.0}, "widget_attrs": {"min": -5.0, "max": 5.0, "step": "0.01"}, "taxonomic_restriction": []},
                {"uuid": "969d04d9-cbc2-45d1-83cd-1d3450fe8a35", "field_class": "IntegerField", "version": 1, "role": "regular", "definition": {"widget": "MobileNumberInput", "required": False, "is_sticky": False, "label": "Integer", "help_text": None, "initial": None}, "position": 9, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "1125a45a-6d38-4874-910d-b2dedcc7dedb", "field_class": "MultipleChoiceField", "version": 2, "role": "regular", "definition": {"widget": "CheckboxSelectMultiple", "required": False, "is_sticky": False, "label": "Checkboxes", "help_text": None, "initial": None, "choices": [["mc3", "mc3"], ["mc2", "mc2"], ["mc1", "mc1"]]}, "position": 10, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []},
                {"uuid": "74763c0c-ea70-4280-940f-5ddb41d74747", "field_class": "PictureField", "version": 1, "role": "regular", "definition": {"widget": "CameraAndAlbumWidget", "required": False, "is_sticky": False, "label": "Images", "help_text": None, "initial": None}, "position": 11, "options": {}, "widget_attrs": {}, "taxonomic_restriction": []}],
            "taxonomic_restriction": [],
            "taxonomic_reference": "7dfd9ff4-456e-426d-9772-df5824dab18f",
            "geographic_reference": "98332a11-d56e-4a92-aeda-13e2f74453cb",
            "temporal_reference": "33cf1019-c8a1-4091-8c23-c95489c39094"
        }
    }
}
'''

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
