from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required

from django.views.generic.edit import DeleteView


"""
    opens a confirmation dialog in a modal
    removes the element from screen
"""
class AjaxDeleteView(DeleteView):
    
    template_name = 'localcosmos_server/generic/delete_object.html'

    def get_model(self):
        return self.model

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        context['deleted_object_id'] = self.object.pk
        context['deleted'] = True
        self.object.delete()
        return self.render_to_response(context)

    def get_deletion_message(self):
        return None

    def get_verbose_name(self):
        return self.object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = ContentType.objects.get_for_model(self.get_model())
        context['verbose_name'] = self.get_verbose_name()
        context['url'] = self.request.path
        context['deletion_message'] = self.get_deletion_message()
        context['deleted'] = False
        context['deletion_object'] = self.object
        return context

    @method_decorator(ajax_required)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
