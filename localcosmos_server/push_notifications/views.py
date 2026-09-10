from django.db.models import Count

from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator

from localcosmos_server.server_control_panel.views import AppMixin
from localcosmos_server.decorators import ajax_required

from localcosmos_server.push_notifications.models import PushNotificationLog, PushReceivingDevice
from localcosmos_server.push_notifications.forms import SendPushNotificationForm
from localcosmos_server.push_notifications.services import PushNotificationService

class ManagePushNotifications(AppMixin, TemplateView):
    template_name = "push_notifications/manage_push_notifications.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['push_notification_logs'] = PushNotificationLog.objects.filter(app=self.request.app)
        counts = {
            entry['language_code']: entry['count']
            for entry in PushReceivingDevice.objects.filter(app=self.request.app)
                .values('language_code')
                .annotate(count=Count('id'))
        }
        context['devices_per_language'] = [
            (lang, counts.get(lang, 0))
            for lang in self.request.app.languages()
        ]
        context['form'] = SendPushNotificationForm(self.request.app)
        return context


class SendPushNotification(AppMixin, FormView):
    
    form_class = SendPushNotificationForm
    template_name = "push_notifications/ajax/send_push_notification_form.html"
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['app'] = self.app
        return kwargs

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        app = kwargs.pop('app')
        return form_class(app, **kwargs)

    def form_valid(self, form):
        app = self.request.app
        title = form.cleaned_data.get('title')
        body = form.cleaned_data.get('body')
        language_code = form.cleaned_data.get('language_code') or None
        data = form.cleaned_data.get('data') or None

        service = PushNotificationService(app, user=self.request.user)
        if language_code:
            fcm_logs = service.send(title, body, language_code=language_code, data=data)
        else:
            for lang in app.languages():
                service.add_translation(lang, title, body, data=data)
            fcm_logs = service.send_translated()

        context = self.get_context_data()
        context['success'] = True
        context['fcm_result'] = fcm_logs
        context['fcm_has_failures'] = any(
            log.status == PushNotificationLog.STATUS_FAILURE for log in fcm_logs
        )
        context['form'] = form

        return self.render_to_response(context)
    

class SendPushNotificationModal(SendPushNotification):
    template_name = "push_notifications/ajax/send_push_notification_modal.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.method == 'GET':
            form.fields['data'].initial = self.request.GET.get('data', '')
        return form
    
    
class GetNotificationLogs(AppMixin, TemplateView):
    template_name = "push_notifications/ajax/notification_logs.html"

    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['push_notification_logs'] = PushNotificationLog.objects.filter(app=self.request.app)
        return context
    