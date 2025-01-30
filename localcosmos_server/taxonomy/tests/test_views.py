from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.tests.common import (test_settings, 
    TESTAPP_NAO_PUBLISHED_ABSOLUTE_PATH, TESTAPP_NAO_PREVIEW_ABSOLUTE_PATH, TESTAPP_NAO_REVIEW_ABSOLUTE_PATH,
    TESTAPP_AO_PUBLISHED_ABSOLUTE_PATH, TESTAPP_AO_PREVIEW_ABSOLUTE_PATH, TESTAPP_AO_REVIEW_ABSOLUTE_PATH,)


from localcosmos_server.taxonomy.views import (SearchAppTaxon, ManageTaxonomicRestrictions,
                                               RemoveAppTaxonomicRestriction)

from localcosmos_server.server_control_panel.tests.test_views import GetViewMixin

from localcosmos_server.tests.mixins import WithApp, WithUser, CommonSetUp

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm, TypedTaxonomicRestrictionForm

import json


# removed WithPublishedApp, which came from online content
@test_settings
class TestSearchAppTaxon(CommonSetUp, WithApp, WithUser, TestCase):
    
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


    def test_get(self):
        self.set_apps()
        self.publish_apps()

        url_kwargs = {
            'app_uid' : self.app.uid,
        }

        get_parameters = {
            'taxon_source': 'taxonomy.sources.col',
            'searchtext' : 'Eich',
            'language' : 'de',
        }

        response = self.client.get(reverse('search_app_taxon', kwargs=url_kwargs), get_parameters)

        self.assertEqual(response.status_code, 200)
        choices = json.loads(response.content)
        

        expected_choices = [{
            'label': 'Eiche',
            'taxon_latname': 'Quercus robur',
            'taxon_author': 'L.',
            'taxon_nuid': '00600800600p0030070db',
            'taxon_source': 'taxonomy.sources.col',
            'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d',
            'verbose_taxon_source_name': 'Catalogue of Life',
        }]
        self.assertEqual(choices, expected_choices)

        # test latname
        get_parameters['searchtext'] = 'Quercu'

        expected_choices_2 = [{
            'label': 'Quercus ',
            'taxon_latname': 'Quercus',
            'taxon_author': '',
            'taxon_nuid': '00600800600p003007',
            'taxon_source': 'taxonomy.sources.col',
            'name_uuid': 'a8fb9529-9794-46ea-9d42-6a67577f5bde',
            'verbose_taxon_source_name': 'Catalogue of Life'
        },
        {
            'label': 'Quercus robur L.',
            'taxon_latname': 'Quercus robur',
            'taxon_author': 'L.',
            'taxon_nuid': '00600800600p0030070db',
            'taxon_source': 'taxonomy.sources.col',
            'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d',
            'verbose_taxon_source_name': 'Catalogue of Life'
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
    
    
    def test_get_new(self):
        self.set_apps()
        self.publish_apps()

        url_kwargs = {
            'app_uid' : self.ao_app.uid,
        }

        get_parameters = {
            'taxon_source': 'taxonomy.sources.col',
            'searchtext' : 'Eich',
            'language' : 'de',
        }

        response = self.client.get(reverse('search_app_taxon', kwargs=url_kwargs), get_parameters)

        self.assertEqual(response.status_code, 200)
        choices = json.loads(response.content)
        
        expected_choices = [{'label': 'Eiche', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'}, {'label': 'Eiche', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'}]
        self.assertEqual(choices, expected_choices)

        # test latname
        get_parameters['searchtext'] = 'Quercu'

        expected_choices_2 = [
            {'label': 'Quercus robur L.', 'taxon_latname': 'Quercus robur', 'taxon_author': 'L.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8561de7e-0a43-4550-9dc6-f0401c986a2d', 'verbose_taxon_source_name': 'Catalogue of Life'},
            {'label': 'Quercus longaeva Salisb., nom. superfl.', 'taxon_latname': 'Quercus longaeva', 'taxon_author': 'Salisb., nom. superfl.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': 'f81297a5-feaf-4364-8066-171e42e6be73', 'verbose_taxon_source_name': 'Catalogue of Life'},
            {'label': 'Quercus robur eurobur A.Camus, not validly publ.', 'taxon_latname': 'Quercus robur eurobur', 'taxon_author': 'A.Camus, not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '8971170b-9d65-489b-8f8d-59631316aeaa', 'verbose_taxon_source_name': 'Catalogue of Life'},
            {'label': 'Quercus robur typica Beck, not validly publ.', 'taxon_latname': 'Quercus robur typica', 'taxon_author': 'Beck, not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '93c3ebe6-8bfe-4949-a6f6-275be534c2c7', 'verbose_taxon_source_name': 'Catalogue of Life'}, {'label': 'Quercus robur vulgaris A.DC., not validly publ.', 'taxon_latname': 'Quercus robur vulgaris', 'taxon_author': 'A.DC., not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '192b1e2b-0002-4f84-9619-95cb9cdf418f', 'verbose_taxon_source_name': 'Catalogue of Life'},
            {'label': 'Quercus robur longipeduncula Ehrh., not validly publ.', 'taxon_latname': 'Quercus robur longipeduncula', 'taxon_author': 'Ehrh., not validly publ.', 'taxon_nuid': '00600800600p0030070db', 'taxon_source': 'taxonomy.sources.col', 'name_uuid': '1cb032c9-5cb0-4101-8818-49829925cc98', 'verbose_taxon_source_name': 'Catalogue of Life'}
        ]

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
class TestManageTaxonomicRestrictions(CommonSetUp, GetViewMixin, WithApp, WithUser, TestCase):

    def get_url_kwargs(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        url_kwargs = {
            'app_uid' : self.app.uid,
            'content_type_id' : user_ctype.id,
            'object_id' : self.user.id,
        }

        return url_kwargs
    

    def test_get_taxon_search_url(self):
        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        view.content_type = user_ctype
        view.content_instance = self.user
        request.app = self.app
        view.app = self.app
        
        url = view.get_taxon_search_url()
        expected_url = reverse('search_app_taxon', kwargs={'app_uid':self.app.uid})
        self.assertEqual(url, expected_url)
        

    def test_get_prefix(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        view.content_type = user_ctype
        view.content_instance = self.user
        view.app = self.app
        
        prefix = view.get_prefix()
        
        expected_prefix = '{0}-{1}'.format(user_ctype.id, self.user.id)
        self.assertEqual(prefix, expected_prefix)
        

    def test_get_form_kwargs(self):
        user_ctype = ContentType.objects.get_for_model(self.user)

        view, request = self.get_view(ManageTaxonomicRestrictions, 'manage_app_taxonomic_restrictions')
        request.app = self.app
        view.content_type = user_ctype
        view.content_instance = self.user
        view.app = self.app
        
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
        view.app = self.app
        
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
        view.app = self.app

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
        view.app = self.app

        prefix = view.get_prefix()

        name_uuid = '1541aa08-7c23-4de0-9898-80d87e9227b4'

        post_data_unprefixed = {
            'taxon_0' : 'taxonomy.sources.col', 
            'taxon_1' : 'Picea abies',
            'taxon_2' : 'Linnaeus',
            'taxon_3' : name_uuid,
            'taxon_4' : '006002009001005007002',
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
        self.assertEqual(restriction.taxon.name_uuid, name_uuid)

        
@test_settings
class TestRemoveAppTaxonomicRestriction(CommonSetUp, GetViewMixin, WithApp, WithUser, TestCase):

    def test_get(self):

        user_ctype = ContentType.objects.get_for_model(self.user)

        restriction = RemoveAppTaxonomicRestriction.model(
            content_type = user_ctype,
            object_id = self.user.id,
            taxon_source = 'taxonomy.sources.col',
            taxon_latname = 'Picea abies',
            taxon_author = 'Linnaeus',
            name_uuid = '1541aa08-7c23-4de0-9898-80d87e9227b4',
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
        
