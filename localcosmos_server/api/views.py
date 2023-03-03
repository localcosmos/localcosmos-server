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
from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

#from drf_spectacular.utils import inline_serializer, extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from rest_framework import status

from localcosmos_server.models import App


from .serializers import (LocalcosmosUserSerializer, RegistrationSerializer, PasswordResetSerializer,
                            TokenObtainPairSerializerWithClientID)

from .permissions import OwnerOnly, AppMustExist

from localcosmos_server.mails import send_registration_confirmation_email

from localcosmos_server.datasets.models import Dataset
from localcosmos_server.models import UserClients

from djangorestframework_camel_case.parser import CamelCaseJSONParser

from drf_spectacular.utils import extend_schema, inline_serializer


##################################################################################################################
#
#   APP UNSPECIFIC API ENDPOINTS
#
##################################################################################################################
            

class APIHome(APIView):
    """
    - does not require an app uuid
    - displays the status of the api
    """

    def get(self, request, *args, **kwargs):
        return Response({'success':True})



class ManageUserClient:

    def update_datasets(self, user, client):
        # update datasets if the user has done anonymous uploads and then registers
        # assign datasets with no user and the given client_id to the now known user
        # this is only valid for android and iOS installations, not browser views
        
        client_datasets = Dataset.objects.filter(client_id=client.client_id, user__isnull=True)

        for dataset in client_datasets:
            dataset.user = user
            dataset.save()


    def get_client(self, user, platform, client_id):

        if platform == 'browser':
            # only one client_id per user and browser
            client = UserClients.objects.filter(user=user, platform='browser').first()

        else:
            # check if the non-browser client is linked to user
            client = UserClients.objects.filter(user=user, client_id=client_id).first()


        # if no client link is present, create one
        if not client:
            client, created = UserClients.objects.get_or_create(
                user = user,
                client_id = client_id,
                platform = platform,
            )

        return client


class RegisterAccount(ManageUserClient, APIView):
    """
    User Account Registration, App specific
    """

    permission_classes = (AppMustExist,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (JSONRenderer,)
    serializer_class = RegistrationSerializer

    # this is for creating only
    def post(self, request, *args, **kwargs):
        serializer_context = { 'request': request }
        serializer = self.serializer_class(data=request.data, context=serializer_context)

        context = { 
            'success' : False,
        }

        if serializer.is_valid():
            app_uuid = kwargs['app_uuid']
            
            user = serializer.create(serializer.validated_data)

            # create the client
            platform = serializer.validated_data['platform']
            client_id = serializer.validated_data['client_id']
            client = self.get_client(user, platform, client_id)
            # update datasets
            self.update_datasets(user, client)

            request.user = user
            context['user'] = LocalcosmosUserSerializer(user).data
            context['success'] = True

            # send registration email
            try:
                send_registration_confirmation_email(user, app_uuid)
            except:
                # todo: log?
                pass
            
        else:
            context['success'] = False
            context['errors'] = serializer.errors
            return Response(context, status=status.HTTP_400_BAD_REQUEST)

        # account creation was successful
        return Response(context)


class ManageAccount(generics.RetrieveUpdateDestroyAPIView):
    '''
        Manage Account
        - authenticated users only
        - owner only
        - [GET] delivers the account as json to the client
        - [POST] validates and saves - and returns json
    '''

    permission_classes = (IsAuthenticated, OwnerOnly)
    authentication_classes = (JWTAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (JSONRenderer,)
    serializer_class = LocalcosmosUserSerializer

    def get_object(self):
        obj = self.request.user
        self.check_object_permissions(self.request, obj)
        return obj
    

# a user enters his email address or username and gets an email
from django.contrib.auth.forms import PasswordResetForm
class PasswordResetRequest(APIView):
    serializer_class = PasswordResetSerializer
    renderer_classes = (JSONRenderer,)
    permission_classes = ()

    def post(self, request, *args, **kwargs):
       
        serializer = self.serializer_class(data=request.data)

        context = {'success': False}
        
        if serializer.is_valid():
            form = PasswordResetForm(data=serializer.data)
            form.is_valid()
            users = form.get_users(serializer.data['email'])
            users = list(users)

            if not users:
                context['error_message'] = _('No matching user found.')
                return Response(context, status=status.HTTP_400_BAD_REQUEST)

            form.save(email_template_name='localcosmos_server/registration/password_reset_email.html')
            context['success'] = True
            
        else:
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
        return Response(context)


from rest_framework_simplejwt.views import TokenObtainPairView
class TokenObtainPairViewWithClientID(ManageUserClient, TokenObtainPairView):

    serializer_class = TokenObtainPairSerializerWithClientID

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        # serializer.user is available
        # user is authenticated now, and serializer.user is available
        # client_ids make sense for android and iOS, but not for browser
        # if a browser client_id exists, use the existing browser client_id, otherwise create one
        # only one browser client_id per user
        platform = request.data['platform']
        client_id = request.data['client_id']

        client = self.get_client(serializer.user, platform, client_id)

        # update datasets
        self.update_datasets(serializer.user, client)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


##################################################################################################################
#
#   APP SPECIFIC API ENDPOINTS
#
##################################################################################################################
'''
    AppAPIHome
'''
class AppAPIHome(APIView):

    @extend_schema(
        responses=inline_serializer('App', {
            'api_status': str,
            'app_name': str,
        })
    )
    def get(self, request, *args, **kwargs):
        app = App.objects.get(uuid=kwargs['app_uuid'])
        context = {
            'api_status' : 'online',
            'app_name' : app.name,
        }
        return Response(context)
