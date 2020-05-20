###################################################################################################################
#
# LOCAL COSMOS API
# - communicatoin between app installations and the lc server
# - some endpoints are app-specific, some are not
# - users have app-specific permissions
# - app endpoint scheme: /<str:app_uuid>/{ENDPOINT}/
#
###################################################################################################################
from django.contrib.auth import logout
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework.views import APIView
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.authtoken.models import Token

from rest_framework import status

from localcosmos_server.models import App

from .serializers import LCAuthTokenSerializer, AccountSerializer, RegistrationSerializer, PasswordResetSerializer
from django_road.permissions import IsAuthenticatedOnly, OwnerOnly
from .authentication import LCTokenAuthentication

from localcosmos_server.mails import send_registration_confirmation_email

import os, json


##################################################################################################################
#
#   APP UNSPECIFIC API ENDPOINTS
#
##################################################################################################################
            

'''
    APIHome
    - does not require an app uuid
    - displays the status of the api
'''
class APIHome(APIView):

    def get(self, request, *args, **kwargs):
        return Response({'success':True})


'''
    APIDocumentation
    - displays endpoints
'''
class APIDocumentation(APIView):
    pass


'''
    Token Authentication
    - does not require an app uuid
    - you authenticate with the server, app-unspecific
    - the app-specific api calls depend on the app-specific user role
'''
from rest_framework.authtoken.views import ObtainAuthToken
class ObtainLCAuthToken(ObtainAuthToken):
    serializer_class = LCAuthTokenSerializer

    # we have tro pass the uuid to the app, rest_framework.authtoken.views.ObtainAuthToken does not do this
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.last_login = timezone.now()
        user.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'uuid':user.uuid})



'''
    User Account Registration, App specific
'''
class RegisterAccount(APIView):

    permission_classes = ()
    renderer_classes = (TemplateHTMLRenderer,)
    template_name = 'localcosmos_server/api/register_account.html'
    serializer_class = RegistrationSerializer


    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class()
        serializer.lc_initial = {
            'client_id': request.GET['client_id'],
            'platform' : request.GET['platform'],
            'app_uuid' : request.GET['app_uuid'],
        }
        serializer_context = {
            'serializer': serializer,
            'request':request,
        }
        return Response(serializer_context)



    # this is for creating only
    def post(self, request, *args, **kwargs):
        
        serializer_context = { 'request': request }        
        serializer = self.serializer_class(data=request.data, context=serializer_context)

        context = {
            'user': request.user,
            'success' : False,
            'request' : request,
        }
        
        if serializer.is_valid():
            app_uuid = serializer.validated_data['app_uuid']
            
            user = serializer.save()
            request.user = user
            context['user'] = user
            context['success'] = True

            # send registration email
            send_registration_confirmation_email(user, app_uuid)
            
        else:
            context['success'] = False
            context['serializer'] = serializer
            return Response(context, status=status.HTTP_400_BAD_REQUEST)

        # account creation was successful
        context['serializer'] = self.serializer_class(data=request.data)
        return Response(context)    




'''
    Manage Account
    - authenticated users only
    - owner only
    - [GET] delivers the form html to the client
    - [POST] validates and saves - and returns html
'''
class ManageAccount(APIView):

    permission_classes = (IsAuthenticatedOnly, OwnerOnly)
    authentication_classes = (LCTokenAuthentication,)
    renderer_classes = (TemplateHTMLRenderer,)
    template_name = 'localcosmos_server/api/manage_account.html'
    serializer_class = AccountSerializer

    def get_object(self):
        obj = self.request.user
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.user)
        serializer_context = {
            'serializer': serializer,
            'user': request.user,
            'request':request
        }
        return Response(serializer_context)

    # this is for updating only
    def put(self, request, *args, **kwargs):
        
        serializer_context = { 'request': request }        
        serializer = self.serializer_class(data=request.data, instance=request.user, context=serializer_context)

        context = {
            'user': request.user,
            'success' : False,
            'request' : request,
        }
        
        if serializer.is_valid():
            serializer.save()
            context['user'] = request.user
        else:
            context['success'] = False
            context['serializer'] = serializer
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
            
        context['serializer'] = serializer
        return Response(context)    


'''
    Delete Account
    - authenticated users only
    - owner only
    - [GET] delivers the form html to the client
    - [DELETE] deletes the account
'''
class DeleteAccount(APIView):

    permission_classes = (IsAuthenticatedOnly, OwnerOnly)
    authentication_classes = (LCTokenAuthentication,)
    renderer_classes = (TemplateHTMLRenderer,)
    template_name = 'localcosmos_server/api/delete_account.html'
    serializer_class = AccountSerializer


    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.user)
        serializer_context = {
            'serializer': serializer,
            'user': request.user,
            'request':request
        }
        return Response(serializer_context)


    def delete(self, request, *args, **kwargs):

        request.user.delete()

        logout(request)

        context = {
            'user': request.user,
            'success' : True,
            'request' : request,
        }
        
        return Response(context)
    

# a user enters his email address or username and gets an email
from django.contrib.auth.forms import PasswordResetForm
class PasswordResetRequest(APIView):

    serializer_class = PasswordResetSerializer
    renderer_classes = (TemplateHTMLRenderer,)
    permission_classes = ()
    
    template_name = 'localcosmos_server/api/password_reset_form.html'


    def get(self, request, *args, **kwargs):
        
        serializer = self.serializer_class()
        serializer_context = {
            'serializer': serializer,
            'request':request,
        }
        
        return Response(serializer_context)


    def post(self, request, *args, **kwargs):

        serializer_context = { 'request': request }        
        serializer = self.serializer_class(data=request.data, context=serializer_context)

        context = {
            'success' : False,
            'request' : request,
        }
        
        if serializer.is_valid():
            form = PasswordResetForm(data=serializer.data)
            form.is_valid()
            users = form.get_users(serializer.data['email'])
            users = list(users)

            if not users:
                context['serializer'] = serializer
                context['error_message'] = _('No matching user found.')
                return Response(context, status=status.HTTP_400_BAD_REQUEST)

            form.save(email_template_name='localcosmos_server/registration/password_reset_email.html')
            context['success'] = True
            
        else:
            context['serializer'] = serializer
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
            
        context['serializer'] = serializer
        return Response(context)    
        

##################################################################################################################
#
#   APP SPECIFIC API ENDPOINTS
#
##################################################################################################################
'''
    AppAPIHome
'''
class AppAPIHome(APIView):

    def get(self, request, *args, **kwargs):
        app = App.objects.get(uuid=kwargs['app_uuid'])
        context = {
            'api_status' : 'online',
            'app_name' : app.name,
        }
        return Response(context)


##################################################################################################################
#
#   LEGAL REQUIREMENTS
#
##################################################################################################################
class PrivacyStatement(APIView):
    
    permission_classes = ()
    renderer_classes = (TemplateHTMLRenderer,)
    template_name = 'localcosmos_server/api/legal/privacy_statement.html'


    def get(self, request, *args, **kwargs):

        app = App.objects.get(uuid=kwargs['app_uuid'])

        # get app legal_notice.json
        review = request.GET.get('review', False)
        if review:
            legal_notice_path = os.path.join(app.review_version_path, 'legal_notice.json')
        else:
            legal_notice_path = os.path.join(app.published_version_path, 'legal_notice.json')
            
        with open(legal_notice_path, 'r') as f:
            legal_notice = json.loads(f.read())
        
        context = {
            'legal_notice' : legal_notice,
            'request':request,
        }
        
        return Response(context)
