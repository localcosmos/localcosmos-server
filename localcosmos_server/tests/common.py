from django.test import TestCase, override_settings
import os

TESTS_ROOT = os.path.dirname(os.path.realpath(__file__))

TEST_IMAGE_PATH = os.path.join(TESTS_ROOT, 'images', 'Leaf.jpg')

LARGE_TEST_IMAGE_PATH = os.path.join(TESTS_ROOT, 'images', 'test-image-2560-1440.jpg')

TEST_MEDIA_ROOT = os.path.join(TESTS_ROOT, 'test_media')

test_settings = override_settings(
    LOCALCOSMOS_OPEN_SOURCE=True,
    LOCALCOSMOS_APPS_ROOT = os.path.join(TESTS_ROOT, 'apps'),
    MEDIA_ROOT = TEST_MEDIA_ROOT,
)



TEST_CLIENT_ID = "4cf82a1d-755b-49e5-b687-a38d78591df4"
TEST_UTC_TIMESTAMP = 1576161098595
TEST_TIMESTAMP_OFFSET = -60

TEST_LATITUDE = 49.63497717058325
TEST_LONGITUDE = 11.091344909741967

TEST_DATASET_DATA_WITH_ALL_REFERENCE_FIELDS = {
    "type": "Dataset",
    "dataset": {
        "type": "Observation",
        "properties": {},
        "reported_values": {
            "client_id": TEST_CLIENT_ID,
            "client_platform": "browser",
            "0f444e85-e31d-443d-afd3-2fa35df08ce3": {"cron": {"type": "timestamp", "format": "unixtime", "timestamp": TEST_UTC_TIMESTAMP, "timezone_offset": TEST_TIMESTAMP_OFFSET}, "type": "Temporal"},
            "7e5c9390-61cf-4cb5-8b0f-9086b2f387ce": {"taxon_nuid": "006002009001005007001", "taxon_uuid": "1541aa08-7c23-4de0-9898-80d87e9227b3", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Picea abies"},
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
                {"role": "regular", "uuid": "96e8ff3b-ffcc-4ccd-b81c-542f37ce53d0", "options": {}, "version": 1, "position": 4, "definition": {"label": "Eichenprozessionsspinner", "widget": "CheckboxInput", "initial": None, "required": False, "help_text": None, "is_sticky": False}, "field_class": "BooleanField", "widget_attrs": {}, "taxonomic_restriction": [{"taxon_nuid": "00600200700q003007", "taxon_uuid": "99000227-c450-4eb4-a6e4-e974d587cdd8", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Quercus", "restriction_type": "exists"}]},
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