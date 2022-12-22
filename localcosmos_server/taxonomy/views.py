from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.http import HttpResponse
from django.urls import reverse
from django.utils.translation import gettext as _

from django.contrib.contenttypes.models import ContentType

import json

from .AppTaxonSearch import AppTaxonSearch
from .forms import AddSingleTaxonForm, TypedTaxonomicRestrictionForm

from localcosmos_server.models import TaxonomicRestriction
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.view_mixins import AppMixin
from localcosmos_server.utils import get_taxon_search_url


class SearchAppTaxon(TemplateView):

    def get(self, request, *args, **kwargs):
        limit = int(request.GET.get('limit', 10))
        searchtext = request.GET.get('searchtext', None)
        language = request.GET.get('language', 'en').lower()
        source = request.GET['taxon_source']
        
        if searchtext:
            search = AppTaxonSearch(request.app, source, searchtext, language, **{'limit':limit})

            choices = search.get_choices_for_typeahead()

        else:
            choices = []
        
        return HttpResponse(json.dumps(choices), content_type="application/json")


'''
    Displays taxonomicrestrictions for an model instance in a model
    - intended for AppTaxa (from disk)
'''
class ManageTaxonomicRestrictionsCommon:

    template_name = 'localcosmos_server/taxonomy/taxonomic_restrictions_form.html'
    form_class= AddSingleTaxonForm

    restriction_model = TaxonomicRestriction


    def get_taxon_search_url(self):
        raise NotImplementedError('ManageTaxonomicRestrictionsCommon subclasses require a get_taxon_search_url method')


    def get_prefix(self):
        prefix = '{0}-{1}'.format(self.content_type.id, self.content_instance.id)
        return prefix

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs.update(self.get_required_form_kwargs())

        return form_kwargs

    def get_required_form_kwargs(self):

        form_kwargs = {
            'prefix' : self.get_prefix(),
            'taxon_search_url' : self.get_taxon_search_url(),
        }

        if settings.LOCALCOSMOS_PRIVATE == True:
            form_kwargs['fixed_taxon_source'] = 'AppTaxa'

        return form_kwargs

    def dispatch(self, request, *args, **kwargs):
        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        Model = self.content_type.model_class()
        self.content_instance = Model.objects.get(pk=kwargs['object_id'])

        self.typed = kwargs.get('typed', None)
        if self.typed == 'typed':
            self.form_class = TypedTaxonomicRestrictionForm

        return super().dispatch(request, *args, **kwargs)

    # if restrictions are available
    # app-admin: only for published apps
    # app-kit: always
    def get_availability(self):
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_available'] = self.get_availability()
        context['content'] = self.content_instance

        restrictions = self.restriction_model.objects.filter(
            content_type=self.content_type,
            object_id=self.content_instance.id,
        )

        context['restrictions'] = restrictions
        return context


    def form_valid(self, form):

        taxon = form.cleaned_data['taxon']

        # currently restrictions apply to all descendants
        taxon.taxon_include_descendants = True

        restriction = self.restriction_model.objects.filter(
            content_type=self.content_type, object_id=self.content_instance.id,
            taxon_latname=taxon.taxon_latname, taxon_author=taxon.taxon_author).first()

        if not restriction:
            
            restriction = self.restriction_model(
                content_type = self.content_type,
                object_id = self.content_instance.id,
                taxon = taxon,
            )

            if 'restriction_type' in form.cleaned_data:
                restriction.restriction_type = form.cleaned_data['restriction_type']

            restriction.save()


        context = self.get_context_data(**self.kwargs)
        context['form'] = self.form_class(**self.get_required_form_kwargs())
        context['success'] = True

        return self.render_to_response(context)

class ManageTaxonomicRestrictions(ManageTaxonomicRestrictionsCommon, AppMixin, FormView):

    def get_taxon_search_url(self):
        return get_taxon_search_url(self.app, self.content_instance)


    def get_availability(self):
        return self.request.app.published_version_path != None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app'] = self.app
        return context
        

class ManageModalTaxonomicRestrictions(ManageTaxonomicRestrictions):
    template_name = 'localcosmos_server/taxonomy/manage_modal_taxonomic_restrictions.html'
    
class RemoveAppTaxonomicRestriction(AjaxDeleteView):

    model = TaxonomicRestriction

    def get_deletion_message(self):
        return _("Do you really want to remove %s?" % self.object.taxon_latname)
