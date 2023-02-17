import os, json, localcosmos_server
from localcosmos_server.tests.common import DataCreator

observation_form_json_path = os.path.join(os.path.dirname(__file__), 'example_files/observation_form.json')

def get_observation_form_example():

    with open(observation_form_json_path, 'rb') as observation_form_file:
        observation_form = json.loads(observation_form_file.read())

    return observation_form


def get_dataset_data_example():

    observation_form_json = get_observation_form_example()

    data_creator = DataCreator()

    data = data_creator(observation_form_json=observation_form_json)
    return data

