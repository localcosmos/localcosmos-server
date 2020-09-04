'''
    AppTaxonSearch
    - search an installed and BUILT app for taxa
'''
import os, json
from localcosmos_server.taxonomy.lazy import LazyAppTaxon

class AppTaxonSearch:

    def __init__(self, app, taxon_source, searchtext, language, **kwargs):
        self.app = app
        self.taxon_source = taxon_source
        self.searchtext = searchtext.upper()
        self.language = language

        self.limit = kwargs.pop('limit', 15)
        self.kwargs = kwargs

        self.vernacular_filepath = None

        if self.app.published_version:
            app_state='published'
        else:
            app_state='preview'
            
        app_features = self.app.get_features(app_state=app_state)

        app_root = app.published_version_path
        self.latname_alphabet_folder = os.path.join(app_root, app_features['BackboneTaxonomy']['alphabet'])
        
        vernacular_relpath = app_features['BackboneTaxonomy']['vernacular'].get(language, None)

        if vernacular_relpath:
            vernacular_filepath = os.path.join(app_root, vernacular_relpath)

            if os.path.isfile(vernacular_filepath):
                self.vernacular_filepath = vernacular_filepath



    def search(self):

        taxa = []

        latname_matches = []
        vernacular_matches = []


        letters = self.searchtext[:2].upper()
        letter_filepath = os.path.join(self.latname_alphabet_folder, '{0}.json'.format(letters))

        if os.path.isfile(letter_filepath):

            with open(letter_filepath, 'r') as f:
                taxon_list = json.loads(f.read())

            for taxon_dic in taxon_list:

                if len(latname_matches) >= self.limit:
                    break

                if taxon_dic['taxon_latname'].upper().startswith(self.searchtext):
                    lazy_taxon = LazyAppTaxon(**taxon_dic)
                    latname_matches.append(lazy_taxon.as_typeahead_choice())


        if self.vernacular_filepath:
            with open(self.vernacular_filepath, 'r') as f:
                vernacular_list = json.loads(f.read())

            for taxon_dic in vernacular_list:

                if len(vernacular_matches) >= self.limit:
                    break
                
                if taxon_dic['name'].upper().startswith(self.searchtext):
                    lazy_taxon = LazyAppTaxon(**taxon_dic)
                    vernacular_matches.append(lazy_taxon.as_typeahead_choice(label=taxon_dic['name']))

        match_count = len(latname_matches) + len(vernacular_matches)
        if match_count > self.limit:

            taxa = latname_matches[:7] + vernacular_matches[:7]

        else:
            taxa = latname_matches + vernacular_matches

        return taxa

    def get_choices_for_typeahead(self):
        return self.search()
