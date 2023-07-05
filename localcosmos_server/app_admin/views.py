from django.shortcuts import render
from django.views.generic import TemplateView, FormView

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.urls import reverse

User = get_user_model()

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from localcosmos_server.models import AppUserRole

from localcosmos_server.datasets.models import DATASET_VALIDATION_DICT, Dataset

HUMAN_INTERACTION_CLASSES = [validation_classpath for validation_classpath, validation_class
                             in DATASET_VALIDATION_DICT.items() if validation_class.is_automatic==False]

from .forms import AppUserRoleForm, SearchAppUserForm

# middleware only grants acces to experts and admins
# AdminOnly is done via Mixin
from .view_mixins import AdminOnlyMixin, ExpertOnlyMixin

import json


'''
    AdminHome
    - display datasets that need validation
'''
class AdminHome(TemplateView):
    template_name = 'app_admin/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)        
        review_datasets = Dataset.objects.filter(app_uuid=self.request.app.uuid,
                                                 validation_step__in=HUMAN_INTERACTION_CLASSES)
        context['review_datasets'] = review_datasets

        no_taxon_datasets = Dataset.objects.filter(app_uuid=self.request.app.uuid, taxon_latname__isnull=True)
        context['no_taxon_datasets'] = no_taxon_datasets
        return context


class UserList(AdminOnlyMixin, TemplateView):

    template_name = 'app_admin/userlist.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        app_admins = AppUserRole.objects.filter(app=self.request.app, role='admin').order_by('user__username')
        app_experts = AppUserRole.objects.filter(app=self.request.app, role='expert').order_by('user__username')
        
        context['app_admins'] = app_admins
        context['app_experts'] = app_experts

        exclude_ids = list(app_admins.values_list('user_id', flat=True)) + list(
            app_experts.values_list('user_id', flat=True))

        context['app_users'] = User.objects.all().exclude(id__in=exclude_ids).exclude(is_superuser=True).exclude(
            is_staff=True).exclude(username='APPKITAPIUSER').order_by('username')

        context['search_app_user_form'] = SearchAppUserForm()
        
        return context
        

class ManageAppUserRole(AdminOnlyMixin, FormView):

    template_name = 'app_admin/manage_app_user_role.html'
    form_class = AppUserRoleForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = User.objects.get(pk=kwargs['user_id'])
        self.user_role = AppUserRole.objects.filter(app=self.request.app, user=self.user).first()
        return super().dispatch(request, *args, **kwargs)


    def get_initial(self):
        initial = super().get_initial()
        if self.user_role:
            initial['role'] = self.user_role.role
        else:
            initial['role'] = 'user'
        return initial


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_user'] = self.user
        return context


    def form_valid(self, form):

        role = form.cleaned_data['role']

        if role == 'user':
            if self.user_role:
                self.user_role.delete()

        else:

            if not self.user_role:
                self.user_role = AppUserRole(
                    app=self.request.app,
                    user=self.user,
                )

            self.user_role.role = form.cleaned_data['role']
            self.user_role.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        context['new_role'] = role
        context['form'] = form

        return self.render_to_response(context)


class SearchAppUser(TemplateView):

    @method_decorator(ajax_required)
    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit',10)
        searchtext = request.GET.get('searchtext', None)

        choices = []

        if searchtext:
        
            results = User.objects.filter(username__istartswith=searchtext)[:10]

            for result in results:
                
                url_kwargs = {
                    'app_uid' :self.request.app.uid,
                    'user_id':result.id,
                }
                
                user = {
                    'name' : result.username,
                    'id' : result.id,
                    'edit_role_url' : reverse('appadmin:manage_app_user_role', kwargs=url_kwargs),
                }

                choices.append(user)
        

        return HttpResponse(json.dumps(choices), content_type='application/json')
    
