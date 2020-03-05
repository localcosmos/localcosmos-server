from django.test import TestCase, RequestFactory
from django.urls import reverse
from django import forms
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.tests.common import test_settings
from localcosmos_server.tests.mixins import WithUser

from localcosmos_server.views import LogIn, LoggedOut
from localcosmos_server.view_mixins import TaxonomicRestrictionMixin

from localcosmos_server.models import TaxonomicRestriction


@test_settings
class TestLogIn(WithUser, TestCase):

    def setUp(self):
        super().setUp()
        self.create_superuser()

    def test_get(self):

        response = self.client.get(reverse('log_in'))
        self.assertEqual(response.status_code, 200)


@test_settings
class TestLoggedOut(WithUser, TestCase):

    def setUp(self):
        super().setUp()
        self.create_superuser()

    def test_get(self):

        response = self.client.get(reverse('loggedout'))
        self.assertEqual(response.status_code, 200)


from localcosmos_server.taxonomy.fields import TaxonField
class FormForTest(forms.Form):
    taxon = TaxonField(taxon_search_url='test', required=False)
    restriction_type = forms.CharField(required=False)
    
@test_settings
class TestTaxonomicRestrictionMixin(WithUser, TestCase):

    def test_save_taxonomic_restriction(self):

        user = self.create_user()

        post_data = {
            'taxon_0': "taxonomy.sources.col",
            'taxon_1': "Picea abies",
            'taxon_2' : "1541aa08-7c23-4de0-9898-80d87e9227b3",
            'taxon_3' : "006002009001005007001",
        }
        
        form = FormForTest(post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        view = TaxonomicRestrictionMixin()
        view.save_taxonomic_restriction(user, form)

        content_type = ContentType.objects.get_for_model(user)
        created_restriction = TaxonomicRestriction.objects.get(content_type=content_type, object_id=user.id)
        self.assertEqual(created_restriction.restriction_type, 'exists')
        self.assertEqual(str(created_restriction.taxon_uuid), post_data['taxon_2'])
        self.assertEqual(created_restriction.taxon_source, post_data['taxon_0'])
        self.assertEqual(created_restriction.taxon_latname, post_data['taxon_1'])
        self.assertEqual(created_restriction.taxon_nuid, post_data['taxon_3'])



    def test_save_taxonomic_restriction_with_type(self):

        user = self.create_user()

        post_data = {
            'taxon_0': "taxonomy.sources.col",
            'taxon_1': "Picea abies",
            'taxon_2' : "1541aa08-7c23-4de0-9898-80d87e9227b3",
            'taxon_3' : "006002009001005007001",
            'restriction_type' : 'optional',
        }
        
        form = FormForTest(post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        view = TaxonomicRestrictionMixin()
        view.save_taxonomic_restriction(user, form)

        content_type = ContentType.objects.get_for_model(user)
        created_restriction = TaxonomicRestriction.objects.get(content_type=content_type, object_id=user.id)
        self.assertEqual(created_restriction.restriction_type, 'optional')
        self.assertEqual(str(created_restriction.taxon_uuid), post_data['taxon_2'])
        self.assertEqual(created_restriction.taxon_source, post_data['taxon_0'])
        self.assertEqual(created_restriction.taxon_latname, post_data['taxon_1'])
        self.assertEqual(created_restriction.taxon_nuid, post_data['taxon_3'])
        

    def test_save_taxonomic_restriction_no_taxon(self):

        user = self.create_user()

        post_data = {}
        
        form = FormForTest(post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        view = TaxonomicRestrictionMixin()
        view.save_taxonomic_restriction(user, form)

        content_type = ContentType.objects.get_for_model(user)
        created_restriction = TaxonomicRestriction.objects.filter(content_type=content_type, object_id=user.id)
        self.assertFalse(created_restriction.exists())

        