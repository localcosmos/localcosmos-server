from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string, get_template
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.translation import gettext as _

FROM_EMAIL = settings.DEFAULT_FROM_EMAIL

from localcosmos_server.models import App

import os, json

def send_registration_confirmation_email(user, app_uuid):

    app = App.objects.get(uuid=app_uuid)

    legal_notice_path = os.path.join(app.published_version_path, 'legal_notice.json')

    # backwards compatibility
    if os.path.isfile(legal_notice_path):
        with open(legal_notice_path, 'r') as f:
            legal_notice = json.loads(f.read())
        
        subject = _('Registration confirmation')
        from_email = FROM_EMAIL
        to = user.email

        legal_notice_url = reverse('legal_notice', kwargs={'app_uid':app.uid}, urlconf='localcosmos_server.urls')
        privacy_statement_url = reverse('privacy_statement', kwargs={'app_uid':app.uid},
                                        urlconf='localcosmos_server.urls')

        ctx = {
            'user' : user,
            'app' : app,
            'legal_notice' : legal_notice,
            'site' : Site.objects.get_current(),
            'legal_notice_url' : legal_notice_url,
            'privacy_statement_url' : privacy_statement_url,
        }

        text_message = render_to_string('email/registration_confirmation.txt', ctx)
        html_message = get_template('email/registration_confirmation.html').render(ctx)

        msg = EmailMultiAlternatives(subject, text_message, from_email=from_email, to=[to])
        msg.attach_alternative(html_message, 'text/html')
        
        msg.send()
