from django.views.generic import TemplateView, FormView
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from localcosmos_server.models import App

from .models import UserPoints, PointRule, PointRuleCondition
from localcosmos_server.view_mixins import AppMixin
from localcosmos_server.generic_views import AjaxDeleteView

from .forms import PointRuleForm, DatasetConditionForm, TaxonConditionForm, GeographyConditionForm

from django.utils.decorators import method_decorator
from localcosmos_server.decorators import ajax_required


class ListAchievements(AppMixin, TemplateView):
    template_name = 'achievements/achievements_list.html'


class GetPointRues(AppMixin, TemplateView):
    template_name = 'achievements/ajax/point_rules_list.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['point_rules_ctype'] = ContentType.objects.get_for_model(PointRule)
        context['point_rules'] = PointRule.objects.filter(app=self.app).order_by('position')
        return context
    
    
class ManagePointRule(AppMixin, FormView):
    template_name = 'achievements/ajax/manage_point_rule.html'
    form_class = PointRuleForm
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        self.set_point_rule(**kwargs)
        return super().dispatch(*args, **kwargs)
    
    def set_point_rule(self, **kwargs):
        app = App.objects.get(uid=kwargs['app_uid'])
        rule_id = self.kwargs.get('rule_id')
        self.point_rule = None
        if rule_id:
            self.point_rule = PointRule.objects.get(app=app, id=rule_id)
            
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['language'] = self.app.primary_language
        if self.point_rule is not None:
            kwargs['instance'] = self.point_rule
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['point_rule'] = self.point_rule
        context['success'] = False
        return context
    
    
    def form_valid(self, form):
        self.point_rule = form.save(commit=False)
        self.point_rule.app = self.app
        self.point_rule.save()
        
        context = self.get_context_data()
        context['success'] = True
        
        return self.render_to_response(context)


class DeletePointRule(AppMixin, AjaxDeleteView):
    model = PointRule


class ManageDatasetCondition(AppMixin, FormView):
    template_name = 'achievements/ajax/manage_point_rule_condition.html'
    form_class = DatasetConditionForm
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        self.set_condition(**kwargs)
        return super().dispatch(*args, **kwargs)
    
    def set_condition(self, **kwargs):
        app = App.objects.get(uid=kwargs['app_uid'])
        condition_id = self.kwargs.get('condition_id')
        self.condition = None
        self.point_rule = PointRule.objects.get(id=kwargs['rule_id'])
        
        self.action_url =  reverse('achievements:add_dataset_condition', args=[app.uid, self.point_rule.id])
        
        if condition_id:
            self.condition = PointRuleCondition.objects.get(id=condition_id)
            self.action_url = reverse('achievements:edit_dataset_condition', args=[app.uid, self.point_rule.id, self.condition.id])
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['point_rule'] = self.point_rule
        context['condition'] = self.condition
        context['action_url'] = self.action_url
        return context

    def form_valid(self, form):
        if self.condition is None:
            self.condition = PointRuleCondition(rule=self.point_rule)

        self.condition.factor_type = form.cleaned_data['factor_type']
        self.condition.operator = 'equals'
        self.condition.value_json = True
        self.condition.rule = self.point_rule
        self.condition.save()

        context = self.get_context_data()
        context['success'] = True

        return self.render_to_response(context)
            
class ManageTaxonCondition(AppMixin, FormView):
    template_name = 'achievements/ajax/manage_point_rule_condition.html'
    form_class = TaxonConditionForm
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        self.set_condition(**kwargs)
        return super().dispatch(*args, **kwargs)
    
    def set_condition(self, **kwargs):
        condition_id = self.kwargs.get('condition_id')
        self.condition = None
        self.point_rule = PointRule.objects.get(id=kwargs['rule_id'])
        if condition_id:
            self.condition = PointRuleCondition.objects.get(id=condition_id)
            
class ManageGeographyCondition(AppMixin, FormView):
    template_name = 'achievements/ajax/manage_point_rule_condition.html'
    form_class = GeographyConditionForm
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        self.set_condition(**kwargs)
        return super().dispatch(*args, **kwargs)
    
    def set_condition(self, **kwargs):
        condition_id = self.kwargs.get('condition_id')
        self.condition = None
        self.point_rule = PointRule.objects.get(id=kwargs['rule_id'])
        if condition_id:
            self.condition = PointRuleCondition.objects.get(id=condition_id)

    
    
class DeletePointRuleCondition(AppMixin, AjaxDeleteView):
    model = PointRuleCondition