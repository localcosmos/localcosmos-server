from django.test import TestCase

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm, TypedTaxonomicRestrictionForm


class TestAddSingleTaxonForm(TestCase):

    def test__init__(self):

        with self.assertRaises(ValueError):
            form = AddSingleTaxonForm()

        form = AddSingleTaxonForm(taxon_search_url='test')
        self.assertIn('taxon', form.fields)
        self.assertTrue(form.fields['taxon'].required)


    def test__init__fixed_taxon_source(self):

        form = AddSingleTaxonForm(taxon_search_url='test', fixed_taxon_source='taxonomy.source.col')
        self.assertIn('taxon', form.fields)
        self.assertTrue(form.fields['taxon'].required)

    def test__init__descendants_choice(self):

        form = AddSingleTaxonForm(taxon_search_url='test', descendants_choice=True)
        self.assertIn('taxon', form.fields)
        self.assertTrue(form.fields['taxon'].required)

