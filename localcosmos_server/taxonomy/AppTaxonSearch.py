'''
    AppTaxonSearch
    - search an installed and BUILT app for taxa
'''
import os, json
from django.conf import settings
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
            self.app_root = app.published_version_path
            
        elif settings.LOCALCOSMOS_PRIVATE == False:
            app_state='preview'
            self.app_root = app.preview_version_path
            
        else:
            raise ValueError('You tried to use preview mode on a Local Cosmos private Server. This is not supported.')
            
        self.app_features = self.app.get_features(app_state=app_state)
        
        
        self.taxon_latname_search_filepath = self.get_taxon_latname_search_filepath()
        self.vernacular_search_filepath = self.get_vernacular_search_filepath()


    def get_vernacular_search_filepath(self):
        
        filepath = None
        
        if 'search' in self.app_features['BackboneTaxonomy']:
            
            if 'vernacular' in self.app_features['BackboneTaxonomy']['search']:
                
                vernacular_folder = self.app_features['BackboneTaxonomy']['search']['vernacular'].get(self.language, None)

                if vernacular_folder:
                    vernacular_folder = vernacular_folder.lstrip('/')
                    start_letter = self.searchtext[:1].upper()
                    letter_filepath = os.path.join(vernacular_folder, '{0}.json'.format(start_letter))
                    filepath = os.path.join(self.app_root, letter_filepath)
                    
        elif 'vernacular' in self.app_features['BackboneTaxonomy']:
            vernacular_relpath = self.app_features['BackboneTaxonomy']['vernacular'].get(self.language, None)
            if vernacular_relpath:
                filepath = os.path.join(self.app_root, vernacular_relpath.lstrip('/'))

        if os.path.isfile(filepath):
            return filepath

        return None
    
    
    def get_taxon_latname_search_filepath(self):
        
        filepath = None
        
        if len(self.searchtext) >= 2:
            
            if 'search' in self.app_features['BackboneTaxonomy']:
                start_letter = self.searchtext[:1].upper()
                relative_folder_path = self.app_features['BackboneTaxonomy']['search']['taxonLatname'].lstrip('/')
                taxon_latname_search_folder = os.path.join(self.app_root, relative_folder_path)
                filepath = os.path.join(taxon_latname_search_folder, '{0}.json'.format(start_letter))
            
            # backwards compatibility
            elif 'alphabet' in self.app_features['BackboneTaxonomy']:
                letters = self.searchtext[:2].upper()
                relative_folder_path = self.app_features['BackboneTaxonomy']['alphabet'].lstrip('/')
                taxon_latname_search_folder = os.path.join(self.app_root, relative_folder_path)
                filepath = os.path.join(taxon_latname_search_folder, '{0}.json'.format(letters))
        
        if os.path.isfile(filepath):
            return filepath
        return None    

    def search(self):
        
        taxa = []
        latname_matches = []
        vernacular_matches = []
        
        if self.taxon_latname_search_filepath:

            with open(self.taxon_latname_search_filepath, 'r') as f:
                taxon_list = json.loads(f.read())

            for taxon_dic in taxon_list:

                if len(latname_matches) >= self.limit:
                    break

                if taxon_dic['taxonLatname'].upper().startswith(self.searchtext):
                    lazy_taxon = LazyAppTaxon(**taxon_dic)
                    latname_matches.append(lazy_taxon.as_typeahead_choice())


        if self.vernacular_search_filepath:
            
            with open(self.vernacular_search_filepath, 'r') as f:
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
