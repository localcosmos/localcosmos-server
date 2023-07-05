from django.core.management.base import BaseCommand, CommandError

from django.contrib.auth import get_user_model

from localcosmos_server.models import App

import os, json, random, time

from localcosmos_server.datasets.models import ObservationForm, Dataset, DatasetImages

User = get_user_model()

DATASET_COUNT = 50

'''
    create an app in the languages english, german and japanese (testing characters)
'''
class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        for app in App.objects.all():

            # TaxonField requires app
            self.app = app
            self.features = app.get_features(app_state='review')

            self.installed_app_path = app.get_installed_app_path('review')

            if len(self.installed_app_path) > 0 and os.path.exists(self.installed_app_path) and 'GenericForm' in self.features:

                generic_forms = self.features['GenericForm']['list']

                for generic_form_entry in generic_forms:

                    relative_path = generic_form_entry['path'].lstrip('/')
                    generic_form_json_path = os.path.join(self.installed_app_path, relative_path)

                    with open(generic_form_json_path, 'r') as generic_form_file:
                        generic_form_json = json.loads(generic_form_file.read())

                    generic_form_uuid = generic_form_json['uuid']
                    generic_form_version = generic_form_json['version']

                    observation_form = ObservationForm.objects.filter(uuid=generic_form_uuid,
                                                                            version=generic_form_version).first()

                    if not observation_form:

                        observation_form = ObservationForm(
                            uuid = generic_form_uuid,
                            version = generic_form_version,
                            definition = generic_form_json,
                        )

                        observation_form.save()

                    for i in range(0, DATASET_COUNT):

                        data = {}

                        for field in generic_form_json['fields']:

                            field_class = field['fieldClass']
                            method_name = 'get_{0}_value'.format(field_class)
                            data_method = getattr(self, method_name)

                            field_data = data_method(field)

                            data[field['uuid']] = field_data

                        user = self.get_user()
                        client_id = self.get_client_id(user=user)
                        
                        dataset = Dataset(
                            app_uuid = app.uuid,
                            observation_form=observation_form,
                            data=data,
                            client_id=client_id,
                            user=user,
                            platform='browser',
                        )

                        dataset.save()


    def get_user(self):

        if bool(random.getrandbits(1)):
            users = User.objects.all()

            if users:

                user_count = users.count()

                user_index = random.randint(0, user_count-1)

                return users[user_index]

        return None

    
    def get_client_id(self, user=None):
        if user:
            return 'userclient_'.format(user.username)
        return 'test_client'

    def get_TaxonField_value(self, field=None):
        
        taxon_profiles_registry_relative_path = self.features['TaxonProfiles']['registry'].lstrip('/')
        registry_path = os.path.join(self.installed_app_path, taxon_profiles_registry_relative_path)

        with open(registry_path, 'r') as registry_file:
            registry = json.loads(registry_file.read())

        uuids = list(registry.keys())

        uuid_index = random.randint(0, len(uuids) -1)

        uuid = uuids[uuid_index]

        taxon_profile = registry[uuid]

        taxon = {
            'taxonSource': taxon_profile['taxonSource'],
            'taxonLatname': taxon_profile['taxonLatname'],
            'taxonAuthor': taxon_profile['taxonAuthor'],
            'nameUuid': taxon_profile['nameUuid'],
            'taxonNuid': taxon_profile['taxonNuid'],
        }

        return taxon

    def get_PointJSONField_value(self, field=None):
        
        min_long = 6
        max_long = 15
        min_lat = 47
        max_lat = 55

        min_dec = 0
        max_dec = 99999999999

        long = float('{0}.{1}'.format(random.randint(min_long, max_long), random.randint(min_dec, max_dec)))
        lat = float('{0}.{1}'.format(random.randint(min_lat, max_lat), random.randint(min_dec, max_dec)))

        point_data = {
            "type": "Feature",
            "geometry": {
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "EPSG:4326"
                    }
                },
                "type": "Point",
                "coordinates": [long, lat]
            },
            "properties": {
                "accuracy": 1
            }
        }

        return point_data

    def get_GeoJSONField_value(self, field=None):
        poly_1 = [
            [
            [
                8.9758301,
                47.8463443
            ],
            [
                8.9703369,
                47.4726629
            ],
            [
                9.8547363,
                47.4652362
            ],
            [
                9.7943115,
                47.8057761
            ],
            [
                8.9758301,
                47.8463443
            ]
            ]
        ]

        poly_2 =  [
            [
            [
                11.4086151,
                53.7645431
            ],
            [
                11.4189148,
                53.5937274
            ],
            [
                11.5157318,
                53.5998399
            ],
            [
                11.4944458,
                53.7799637
            ],
            [
                11.4086151,
                53.7645431
            ]
            ]
        ]

        polys = [poly_1, poly_2]

        poly_index = random.randint(0,1)

        coordinates = polys[poly_index]

        geojson = {
            "type": "Feature",
            "geometry": {
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "EPSG:4326"
                    }
                },
                "type": "Polygon",
                "coordinates": coordinates
            },
            "properties": {}
        }

        return geojson

    def get_DecimalField_value(self, field=None):
        return round(random.uniform(1.01, 5.99), 2)

    def get_FloatField_value(self, field=None):
        return round(random.uniform(33.33, 66.66), 2)

    def get_IntegerField_value(self, field_=None):
        return random.randint(1, 10)

    def get_CharField_value(self, field=None):
        return 'Lorem ipsum'

    def get_ChoiceField_value(self, field):
        choices = field['definition']['choices']
        choice_count = len(choices)
        choice_index = random.randint(0, choice_count -1)

        choice = choices[choice_index]

        return choice[0]

    def get_MultipleChoiceField_value(self, field):
        
        choices = field['definition']['choices']
        choice_count = len(choices)

        number_of_choices = random.randint(0, choice_count)

        value_set = set([])
        
        for i in range(0, number_of_choices):
            choice_index = random.randint(0, choice_count -1)
            choice = choices[choice_index]
            value_set.add(choice[0])

        return list(value_set)


    def get_DateTimeJSONField_value(self, field=None):
        
        min_utc = 1675250931000 # milliseconds
        offset = -60 # minutes
        now_milli = round(time.time()*1000)

        timestamp = random.randint(min_utc, now_milli)

        cron_data = {
            "cron": {
                "type": "timestamp",
                "format": "unixtime",
                "timestamp": timestamp,
                "timezoneOffset": offset
            },
            "type": "Temporal"
        }

        return cron_data

    def get_BooleanField_value(self, field=None):
        return bool(random.getrandbits(1))

    def get_PictureField_value(self, field=None):
        return None



