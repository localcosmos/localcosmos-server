from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, connection

from localcosmos_server.decorators import ajax_required
from localcosmos_server.forms import SeoParametersForm, ExternalMediaForm
from localcosmos_server.models import EXTERNAL_MEDIA_TYPES

from django.views.generic.edit import DeleteView
from django.views.generic import TemplateView, FormView
from django.http import JsonResponse, Http404

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
    
    
# the media type if fetched from url or instance
class ManageExternalMedia(FormView):
    
    form_class = ExternalMediaForm
    external_media_model_class = None
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_instances(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_instances(self, **kwargs):
        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        self.model_class = self.content_type.model_class()
        self.object_id = kwargs['object_id']
        self.external_media_object = self.model_class.objects.get(pk=self.object_id)
        
        self.external_media = None
        self.media_type = kwargs.get('media_type', None)
        
        allowed_media_types = [mt[0] for mt in EXTERNAL_MEDIA_TYPES]

        if self.media_type and self.media_type not in allowed_media_types:
            raise Http404('Invalid external media type')
        
        if 'external_media_id' in kwargs:
            self.external_media = self.external_media_model_class.objects.filter(
                pk=kwargs['external_media_id']
            ).first()

            self.media_type = self.external_media.media_type

    def get_initial(self):
        initial = super().get_initial()
        if self.external_media:
            initial['url'] = self.external_media.url
            initial['title'] = self.external_media.title
            initial['caption'] = self.external_media.caption
            initial['alt_text'] = self.external_media.alt_text
            initial['author'] = self.external_media.author
            initial['licence'] = self.external_media.licence
        return initial
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = self.content_type
        context['external_media_object'] = self.external_media_object
        context['external_media'] = self.external_media
        context['media_type'] = self.media_type
        context['success'] = False
        return context
    
    
    def create_update(self, cleaned_data):
        
        # check if the instance already has an external media of this type
        if not self.external_media:
            
            self.external_media = self.external_media_model_class.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                url=cleaned_data['url']
            ).first()

            if not self.external_media:
                
                self.external_media = self.external_media_model_class(
                    content_type=self.content_type,
                    object_id=self.object_id,
                )
            

        self.external_media.media_type = self.media_type
        self.external_media.url = cleaned_data['url']
        self.external_media.title = cleaned_data['title']
        self.external_media.caption = cleaned_data['caption']
        self.external_media.alt_text = cleaned_data['alt_text']
        self.external_media.author = cleaned_data['author']
        self.external_media.licence = cleaned_data['licence']
        self.external_media.save()
        
        return self.external_media
    
    
    def form_valid(self, form):
        
        self.external_media = self.create_update(form.cleaned_data)
        
        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        context['form'] = form
        
        return self.render_to_response(context)
