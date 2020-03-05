from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.tests.common import test_settings, MockPost

from localcosmos_server.taxonomy.views import (SearchAppTaxon, ManageTaxonomicRestrictions,
                                               RemoveAppTaxonomicRestriction)

from localcosmos_server.online_content.tests.test_views import WithPublishedApp
from localcosmos_server.server_control_panel.tests.test_views import GetViewMixin

from localcosmos_server.tests.mixins import WithApp, WithUser, CommonSetUp

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm, TypedTaxonomicRestrictionForm


import json


@test_settings
class TestSeachAppTaxon(CommonSetUp, WithPublishedApp, WithApp, WithUser, TestCase):

    def test_get(self):

        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        get_parameters = {
            'taxon_source': 'taxonomy.sources.col',
            'searchtext' : 'Eich',
            'language' : 'en',
        }

        response = self.client.get(reverse('search_app_taxon', kwargs=url_kwargs), get_parameters)

        self.assertEqual(response.status_code, 200)
        choices = json.loads(response.content)

        expected_choices = [{
            'label': 'Eiche',
            'taxon_latname': 'Quercus robur',
            'taxon_nuid': '00600200700q0030070cx',
            'taxon_source': 'taxonomy.sources.col',
            'taxon_uuid': 'fc542c23-258f-4013-bad5-7f9c6a9cfb0d'
        }]
        self.assertEqual(choices, expected_choices)

        # test latname
        get_parameters['searchtext'] = 'Quercu'

        expected_choices_2 = [{
            'label': 'Quercus robur',
            'taxon_latname': 'Quercus robur',
            'taxon_nuid': '00600200700q0030070cx',
            'taxon_source': 'taxonomy.sources.col',
            'taxon_uuid': 'fc542c23-258f-4013-bad5-7f9c6a9cfb0d'
        }]

        response = self.client.get(reverse('search_app_taxon', kwargs=url_kwargs), get_parameters)

        self.assertEqual(response.status_code, 200)
        choices = json.loads(response.content)

        self.assertEqual(choices, expected_choices_2)

        # test no searchtext
        del get_parameters['searchtext']

        response = self.client.get(reverse('search_app_taxon', kwargs=url_kwargs), get_parameters)
        self.assertEqual(response.status_code, 200)
        choices = json.loads(response.content)

        self.assertEqual(choices, [])


@test_settings
class TestManageTaxonomicRestrictions(CommonSetUp, GetViewMixin, WithPublishedApp, WithApp, WithUser, TestCase):

    def get_url_kwargs(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_type_id' : user_ctype.id,
            'object_id' : self.user.id,
        }

        return url_kwargs
    

    def test_get_taxon_search_url(self):

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app
        
        url = view.get_taxon_search_url()
        expected_url = reverse('search_app_taxon', kwargs={'app_uid':self.app.uid})
        self.assertEqual(url, expected_url)
        

    def test_get_prefix(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        view.content_type = user_ctype
        view.content_instance = self.user
        
        prefix = view.get_prefix()
        
        expected_prefix = '{0}-{1}'.format(user_ctype.id, self.user.id)
        self.assertEqual(prefix, expected_prefix)
        

    def test_get_form_kwargs(self):
        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app
        view.content_type = user_ctype
        view.content_instance = self.user
        
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['fixed_taxon_source'], 'AppTaxa')
        self.assertIn('prefix', form_kwargs)
        self.assertIn('taxon_search_url', form_kwargs)
        

    def test_get_required_form_kwargs(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app
        view.content_type = user_ctype
        view.content_instance = self.user
        
        form_kwargs = view.get_required_form_kwargs()
        self.assertEqual(form_kwargs['fixed_taxon_source'], 'AppTaxa')
        self.assertIn('prefix', form_kwargs)
        self.assertIn('taxon_search_url', form_kwargs)


    def test_dispatch(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app

        response = view.dispatch(request, **self.get_url_kwargs())
        self.assertEqual(response.status_code, 200)

        self.assertEqual(view.content_type, user_ctype)
        self.assertEqual(view.content_instance, self.user)
        self.assertEqual(view.form_class, AddSingleTaxonForm)


    def test_dispatch_typed(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app

        url_kwargs = self.get_url_kwargs()
        url_kwargs['typed'] = 'typed'

        response = view.dispatch(request, **url_kwargs)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(view.content_type, user_ctype)
        self.assertEqual(view.content_instance, self.user)
        self.assertEqual(view.form_class, TypedTaxonomicRestrictionForm)
        

    def test_get_availablility(self):

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app

        availability = view.get_availability()
        self.assertTrue(availability)

        self.app.published_version_path = None
        self.app.save()

        availability_2 = view.get_availability()
        self.assertFalse(availability_2)
        

    def test_get_context_data(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        view.content_type = user_ctype
        view.content_instance = self.user
        request.app = self.app

        context = view.get_context_data(**{})
        self.assertTrue(context['is_available'])
        self.assertEqual(context['content'], self.user)
        self.assertEqual(len(context['restrictions']), 0)

    def test_form_valid(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        view.content_type = user_ctype
        view.content_instance = self.user
        request.app = self.app

        prefix = view.get_prefix()

        taxon_uuid = '1541aa08-7c23-4de0-9898-80d87e9227b4'

        post_data_unprefixed = {
            'taxon_0' : 'taxonomy.sources.col', 
            'taxon_1' : 'Picea abies',
            'taxon_2' : taxon_uuid,
            'taxon_3' : '006002009001005007002',
        }

        post_data = {}
        
        for key, value in post_data_unprefixed.items():

            key = '{0}-{1}'.format(prefix, key)

            post_data[key] = value


        form = AddSingleTaxonForm(data=post_data, **view.get_required_form_kwargs())

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        self.assertTrue(response.context_data['success'])

        Model = view.restriction_model
        qry = Model.objects.filter(content_type=user_ctype, object_id=self.user.id)
        self.assertTrue(qry.exists())

        restriction = qry.first()
        self.assertEqual(restriction.taxon.taxon_uuid, taxon_uuid)

        
@test_settings
class TestRemoveAppTaxonomicRestriction(CommonSetUp, GetViewMixin, WithApp, WithUser, TestCase):

    def test_get(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        restriction = RemoveAppTaxonomicRestriction.model(
            content_type = user_ctype,
            object_id = self.user.id,
            taxon_source = 'taxonomy.sources.col',
            taxon_latname = 'Picea abies',
            taxon_uuid = '1541aa08-7c23-4de0-9898-80d87e9227b4',
            taxon_nuid = '006002009001005007002',
        )

        restriction.save()

        url_kwargs = {
            'app_uid' : self.app.uid,
            'pk' : restriction.pk,
        }

        url = reverse('remove_app_taxonomic_restriction', kwargs=url_kwargs)

        response = self.client.get(url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
