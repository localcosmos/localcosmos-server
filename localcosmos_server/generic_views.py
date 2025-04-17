from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required
from localcosmos_server.forms import SeoParametersForm

from django.views.generic.edit import DeleteView
from django.views.generic import TemplateView, FormView
from django.http import JsonResponse

import json


"""
    opens a confirmation dialog in a modal
    removes the element from screen
"""
class AjaxDeleteView(DeleteView):
    
    template_name = 'localcosmos_server/generic/delete_object.html'


    @method_decorator(ajax_required)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_deletion_message(self):
        return None

    def get_verbose_name(self):
        return self.object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = ContentType.objects.get_for_model(self.model)
        context['verbose_name'] = self.get_verbose_name()
        context['url'] = self.request.path
        context['deletion_message'] = self.get_deletion_message()
        context['deleted'] = False
        context['deletion_object'] = self.object
        return context

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)
        context['deleted_object_id'] = self.object.pk
        context['deleted'] = True
        self.object.delete()
        return self.render_to_response(context)

'''
    generic view for storing the order of elements, using the position attribute
'''
from django.db import transaction, connection
class StoreObjectOrder(TemplateView):

    def _on_success(self):
        pass

    def get_save_args(self, obj):
        return []

    @method_decorator(ajax_required)
    def post(self, request, *args, **kwargs):

        success = False

        order = request.POST.get('order', None)

        if order:
            
            self.order = json.loads(order)

            self.ctype = ContentType.objects.get(pk=kwargs['content_type_id'])
            self.model = self.ctype.model_class()

            self.objects = self.model.objects.filter(pk__in=self.order)

            for obj in self.objects:
                position = self.order.index(obj.pk) + 1
                obj.position = position
                save_args = self.get_save_args(obj)
                obj.save(*save_args)

            '''
            with transaction.atomic():

                for obj in self.objects:
                    position = self.order.index(obj.pk) + 1

                    if len(self.order) >= 30:
                        cursor = connection.cursor()
                        cursor.execute("UPDATE %s SET position=%s WHERE id=%s" %(self.model._meta.db_table,
                                                                                 '%s', '%s'),
                                       [position, obj.id])
                    else:
                        obj.position = position
                        save_args = self.get_save_args(obj)
                        obj.save(*save_args)
            '''

            self._on_success()

            success = True
        
        return JsonResponse({'success':success})
    

class ManageSeoParameters(FormView):
    
    form_class = SeoParametersForm
    seo_model_class = None
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_instances(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_instances(self, **kwargs):
        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        self.model_class = self.content_type.model_class()
        self.object_id = kwargs['object_id']
        self.instance = self.model_class.objects.get(pk=self.object_id)
        
        self.seo_parameters = self.seo_model_class.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id
        ).first()
    
    def get_initial(self):
        initial = super().get_initial()
        
        if self.seo_parameters:
            initial['title'] = self.seo_parameters.title
            initial['meta_description'] = self.seo_parameters.meta_description
            
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = self.content_type
        context['instance'] = self.instance
        context['seo_parameters'] = self.seo_parameters
        context['success'] = False
        return context
    
    def create_update_delete(self, cleaned_data):
            
        seo_parameters = self.seo_model_class.objects.filter(content_type=self.content_type, object_id=self.object_id).first()
        if not seo_parameters:
            seo_parameters = self.seo_model_class(content_type=self.content_type, object_id=self.object_id)
            
        title = cleaned_data['title']
        meta_description = cleaned_data['meta_description']
        
        if title or meta_description:
            seo_parameters.title = title
            seo_parameters.meta_description = meta_description
            seo_parameters.save()
        else:
            if seo_parameters and seo_parameters.pk:
                seo_parameters.delete()
                seo_parameters = None
        
        return seo_parameters

    def form_valid(self, form):
        
        self.seo_parameters = self.create_update_delete(form.cleaned_data)
        
        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        context['form'] = form
        
        return self.render_to_response(context)