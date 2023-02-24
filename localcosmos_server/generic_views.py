from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required

from django.views.generic.edit import DeleteView
from django.views.generic import TemplateView
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