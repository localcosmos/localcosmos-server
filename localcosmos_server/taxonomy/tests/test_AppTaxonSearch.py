from django.test import TestCase


from localcosmos_server.tests.common import test_settings

from localcosmos_server.taxonomy.AppTaxonSearch import AppTaxonSearch

from localcosmos_server.tests.mixins import WithApp, WithUser, CommonSetUp

from localcosmos_server.tests.common import (test_settings,
    TESTAPP_NAO_PUBLISHED_ABSOLUTE_PATH, TESTAPP_NAO_PREVIEW_ABSOLUTE_PATH, TESTAPP_NAO_REVIEW_ABSOLUTE_PATH,
    TESTAPP_AO_PUBLISHED_ABSOLUTE_PATH, TESTAPP_AO_PREVIEW_ABSOLUTE_PATH, TESTAPP_AO_REVIEW_ABSOLUTE_PATH,)


import json


# removed WithPublishedApp, which came from online content
@test_settings
class TestAppTaxonSearch(CommonSetUp, WithApp, WithUser, TestCase):
    
    def setUp(self):
        super().setUp()
        self.taxon_source = 'taxonomy.sources.col'
        
    def set_apps(self):
        self.app.preview_version_path = TESTAPP_NAO_PREVIEW_ABSOLUTE_PATH
        self.ao_app.preview_version_path = TESTAPP_AO_PREVIEW_ABSOLUTE_PATH
        
        self.app.save()
        self.ao_app.save()
        
    def publish_apps(self):
        self.app.published_version_path = TESTAPP_NAO_PUBLISHED_ABSOLUTE_PATH
        self.ao_app.published_version_path = TESTAPP_AO_PUBLISHED_ABSOLUTE_PATH
        
        self.app.published_version = 1
        self.ao_app.published_version = 1
        
        self.app.save()
        self.ao_app.save()



    def test_init(self):
        self.set_apps()
        self.publish_apps()
        
        language = 'de'
        searchtext = 'Eich'
        
        #no kwargs
        app_taxon_search = AppTaxonSearch(self.app, self.taxon_source, searchtext, language)
        
        self.assertEqual(app_taxon_search.app, self.app)
        self.assertEqual(app_taxon_search.taxon_source, self.taxon_source)
        self.assertEqual(app_taxon_search.searchtext, 'EICH')
        self.assertEqual(app_taxon_search.language, 'de')
        self.assertEqual(app_taxon_search.kwargs, {})
        self.assertEqual(app_taxon_search.app, self.app)
        self.assertEqual(app_taxon_search.app_root, TESTAPP_NAO_PUBLISHED_ABSOLUTE_PATH)
        self.assertEqual(app_taxon_search.limit, 15)
        
        app_features = app_taxon_search.app_features
        self.assertEqual(app_taxon_search.app_features['PUBLISHED'], True)
        self.assertEqual(app_taxon_search.app_features['PREVIEW'], False)
        self.assertEqual(app_taxon_search.app_features['REVIEW'], False)
        
        # all kwargs
        kwargs = {
            'limit' : 4,
        }
        
        app_taxon_search = AppTaxonSearch(self.app, self.taxon_source, searchtext, language, **kwargs)
        self.assertEqual(app_taxon_search.limit, 4)
        
        self.assertEqual(app_taxon_search.taxon_latname_search_filepath, None)
        self.assertTrue(app_taxon_search.vernacular_search_filepath.endswith(
            'localcosmos/features/BackboneTaxonomy/c71c0a7e-d7a0-4029-94c4-b459e696ccd7/vernacular/de.json'))
        

    def test_get_vernacular_search_filepath(self):
        self.set_apps()
        self.publish_apps()
        
        searchtext = 'eich'
        language = 'de'
        
        # old app layout
        app_taxon_search = AppTaxonSearch(self.app, self.taxon_source, searchtext, language)
        old_path = app_taxon_search.get_vernacular_search_filepath()
        self.assertTrue(old_path.endswith(
            'localcosmos/features/BackboneTaxonomy/c71c0a7e-d7a0-4029-94c4-b459e696ccd7/vernacular/de.json'))
        
        # new app layout
        app_taxon_search = AppTaxonSearch(self.ao_app, self.taxon_source, searchtext, language)
        new_path = app_taxon_search.get_vernacular_search_filepath()
        self.assertTrue(new_path.endswith('localcosmos/features/BackboneTaxonomy/c71c0a7e-d7a0-4029-94c4-b459e696ccd7/search/vernacular/de/E.json'))
        
    
    def test_get_taxon_latname_search_filepath(self):
        self.set_apps()
        self.publish_apps()
        
        searchtext = 'quercus ro'
        language = 'de'
        
        # old app layout
        app_taxon_search = AppTaxonSearch(self.app, self.taxon_source, searchtext, language)
        old_path = app_taxon_search.get_taxon_latname_search_filepath()
        self.assertTrue(old_path.endswith(
            'localcosmos/features/BackboneTaxonomy/c71c0a7e-d7a0-4029-94c4-b459e696ccd7/alphabet/QU.json'))
        
        # new app layout
        app_taxon_search = AppTaxonSearch(self.ao_app, self.taxon_source, searchtext, language)
        new_path = app_taxon_search.get_taxon_latname_search_filepath()
        self.assertTrue(new_path.endswith('localcosmos/features/BackboneTaxonomy/c71c0a7e-d7a0-4029-94c4-b459e696ccd7/search/taxon_latname/Q.json'))
        
    
    def test_search_latnames(self):
        self.set_apps()
        self.publish_apps()
        
        # latname
        searchtext = 'quercus ro'
        language = 'de'
        app_taxon_search = AppTaxonSearch(self.app, self.taxon_source, searchtext, language)
        
        results = app_taxon_search.search()
        expected_results = [{'label': 'Quercus robur L.', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'}]
    
        self.assertEqual(results, expected_results)
        
        # new app
        app_taxon_search = AppTaxonSearch(self.ao_app, self.taxon_source, searchtext, language)
        
        results_2 = app_taxon_search.search()
        expected_results_2 = [
            {'label': 'Quercus robur L.', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'},
            {'label': 'Quercus robur eurobur A.Camus, not validly publ.', 'taxon_latname': 'Quercus robur eurobur', 'taxon_author': 'A.Camus, not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8971170b-9d65-489b-8f8d-59631316aeaa', 'verbose_taxon_source_name': 'Catalogue of Life'}, {'label': 'Quercus robur typica Beck, not validly publ.', 'taxon_latname': 'Quercus robur typica', 'taxon_author': 'Beck, not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '93c3ebe6-8bfe-4949-a6f6-275be534c2c7', 'verbose_taxon_source_name': 'Catalogue of Life'}, {'label': 'Quercus robur vulgaris A.DC., not validly publ.', 'taxon_latname': 'Quercus robur vulgaris', 'taxon_author': 'A.DC., not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '192b1e2b-0002-4f84-9619-95cb9cdf418f', 'verbose_taxon_source_name': 'Catalogue of Life'}, {'label': 'Quercus robur longipeduncula Ehrh., not validly publ.', 'taxon_latname': 'Quercus robur longipeduncula', 'taxon_author': 'Ehrh., not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '1cb032c9-5cb0-4101-8818-49829925cc98', 'verbose_taxon_source_name': 'Catalogue of Life'}
        ]
        self.assertEqual(results_2, expected_results_2)

        
        
    def test_search_vernacular(self):
        self.set_apps()
        self.publish_apps()
        
        # latname
        searchtext = 'eic'
        language = 'de'
        app_taxon_search = AppTaxonSearch(self.app, self.taxon_source, searchtext, language)
        
        results = app_taxon_search.search()
        expected_results = [{'label': 'Eiche', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'}]
        
        self.assertEqual(results, expected_results)
        
        # new app
        app_taxon_search = AppTaxonSearch(self.ao_app, self.taxon_source, searchtext, language)
        
        results_2 = app_taxon_search.search()
        expected_results_2 = [{'label': 'Eiche', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'}, {'label': 'Eiche', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'}]
        self.assertEqual(results_2, expected_results_2)
        
        
    def test_get_choices_for_typeahead(self):
        pass