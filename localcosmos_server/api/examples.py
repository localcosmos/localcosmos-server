import os, json

taxon_profile_json_path = os.path.join(os.path.dirname(__file__), 'example_files/taxon_profile.json')

def get_taxon_profile_example():

    with open(taxon_profile_json_path, 'rb') as taxon_profile_file:
        taxon_profile = json.loads(taxon_profile_file.read())

    return taxon_profile