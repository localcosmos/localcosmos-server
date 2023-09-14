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
from django.conf import settings
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

#from drf_spectacular.utils import inline_serializer, extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from rest_framework import status

from localcosmos_server.models import App, ServerContentImage, LocalcosmosUser


from .serializers import (LocalcosmosUserSerializer, RegistrationSerializer, PasswordResetSerializer,
                            TokenObtainPairSerializerWithClientID, ServerContentImageSerializer)

from .permissions import OwnerOnly, AppMustExist, ServerContentImageOwnerOrReadOnly

from localcosmos_server.mails import send_registration_confirmation_email

from localcosmos_server.datasets.models import Dataset
from localcosmos_server.models import UserClients

from djangorestframework_camel_case.parser import CamelCaseJSONParser, CamelCaseMultiPartParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer

from drf_spectacular.utils import extend_schema, inline_serializer


SERVER_CONTENT_IMAGE_MODEL_MAP = {
    'LocalcosmosUser': LocalcosmosUser
}


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
    renderer_classes = (CamelCaseJSONRenderer,)
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
        - [PUT] validates and saves - and returns json
    '''

    permission_classes = (IsAuthenticated, OwnerOnly)
    authentication_classes = (JWTAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = LocalcosmosUserSerializer

    def get_object(self):
        obj = self.request.user
        self.check_object_permissions(self.request, obj)
        return obj
    

class ManageServerContentImage(APIView):

    permission_classes = (IsAuthenticatedOrReadOnly, ServerContentImageOwnerOrReadOnly)
    authentication_classes = (JWTAuthentication,)
    parser_classes = (CamelCaseMultiPartParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = ServerContentImageSerializer


    # replacement for get_object, checks object level permissions
    def get_object(self, request, **kwargs):

        if 'pk' in kwargs:
            content_image = ServerContentImage.objects.filter(pk=kwargs['pk']).first()
            if not content_image:
                raise Http404

            obj = content_image.content
            self.image_type = content_image.image_type

        else:
            model_name = kwargs['model']
            if model_name not in SERVER_CONTENT_IMAGE_MODEL_MAP:
                raise Http404
                
            model = SERVER_CONTENT_IMAGE_MODEL_MAP[model_name]
            self.image_type = kwargs['image_type']
            obj = model.objects.filter(pk=kwargs['object_id']).first()

            if not obj:
                raise Http404

        # obj is the content instance
        self.check_object_permissions(request, obj)
        return obj


    def get_content_image(self, content_instance, **kwargs):

        content_image = None

        if 'pk' in kwargs:
            content_image = ServerContentImage.objects.get(pk=kwargs['pk'])

        else:
            content_image = content_instance.image(image_type=kwargs['image_type'])

        return content_image

        
    def get(self, request, *args, **kwargs):

        # permission checks, raises 404s
        content_instance = self.get_object(request, **kwargs)

        content_image = self.get_content_image(content_instance, **kwargs)

        if not content_image:
            return Response('', status=status.HTTP_404_NOT_FOUND)

        response_serializer = self.serializer_class(content_image)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    # create
    def post(self, request, *args, **kwargs):

        content_instance = self.get_object(request, **kwargs)

        serializer = self.serializer_class(data=request.data)

        serializer.is_valid()

        if serializer.errors:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_type = kwargs['image_type']

        content_image = self.get_content_image(content_instance, **kwargs)

        old_image_store = None
        if content_image:
            old_image_store = content_image.image_store

        new_content_image = serializer.save(serializer.validated_data, content_instance, image_type, request.user,
            content_image=content_image)

        if old_image_store:
            self.clean_old_image_store(old_image_store)

        response_serializer = self.serializer_class(new_content_image)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    # update
    def put(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


    # delete
    def delete(self, request, *args, **kwargs):
        content_instance = self.get_object(request, **kwargs)

        content_image = self.get_content_image(content_instance, **kwargs)

        if not content_image:
            raise Http404

        old_image_store = content_image.image_store
        content_image.delete()

        self.clean_old_image_store(old_image_store)

        return Response({'deleted': True}, status=status.HTTP_200_OK)
        

    def clean_old_image_store(self, old_image_store):

        related_content_images = ServerContentImage.objects.filter(image_store=old_image_store).exists()

        if not related_content_images:
            old_image_store.delete()

    

# a user enters his email address or username and gets an email
from django.contrib.auth.forms import PasswordResetForm
class PasswordResetRequest(APIView):
    serializer_class = PasswordResetSerializer
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = ()


    def get_from_email(self):
        return None

    def post(self, request, *args, **kwargs):

        app = App.objects.get(uuid=kwargs['app_uuid'])
       
        serializer = self.serializer_class(data=request.data)

        context = {
            'success': False
        }
        
        if serializer.is_valid():
            form = PasswordResetForm(data=serializer.data)
            form.is_valid()
            users = form.get_users(serializer.data['email'])
            users = list(users)

            if not users:
                context['detail'] = _('No matching user found.')
                return Response(context, status=status.HTTP_400_BAD_REQUEST)

            extra_email_context = {
                'app': app,
            }

            form.save(email_template_name='localcosmos_server/app/registration/password_reset_email.html',
                subject_template_name='localcosmos_server/app/registration/password_reset_subject.txt',
                extra_email_context=extra_email_context)
            context['success'] = True
            
        else:
            context.update(serializer.errors)
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(context, status=status.HTTP_200_OK)


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


##################################################################################################################
#
#   ANYCLUSTER POSTGRESQL SCHEMA AWARE WIEWS
#
##################################################################################################################
from anycluster.api.views import (GridCluster, KmeansCluster, GetClusterContent, GetAreaContent, GetDatasetContent,
    GetMapContentCount, GetGroupedMapContents)


class SchemaSpecificMapClusterer:

    def get_schema_name(self, request):

        schema_name = 'public'

        if settings.LOCALCOSMOS_PRIVATE == False:
            schema_name = request.tenant.schema_name

        return schema_name
        

class SchemaGridCluster(SchemaSpecificMapClusterer, GridCluster):
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

class SchemaKmeansCluster(SchemaSpecificMapClusterer, KmeansCluster):
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

class SchemaGetClusterContent(SchemaSpecificMapClusterer, GetClusterContent):
    parser_classes = (JSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

# the client expects imageUrl, not image_url
class SchemaGetAreaContent(SchemaSpecificMapClusterer, GetAreaContent):
    parser_classes = (JSONParser,)
    #renderer_classes = (JSONRenderer,)

class SchemaGetDatasetContent(SchemaSpecificMapClusterer, GetDatasetContent):
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

class SchemaGetMapContentCount(SchemaSpecificMapClusterer, GetMapContentCount):
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

'''
    A taxon definition (taxonLatname etc) is returned, so use CamelCaseRenderer
'''
class SchemaGetGroupedMapContents(SchemaSpecificMapClusterer, GetGroupedMapContents):
    parser_classes = (JSONParser,)
    #renderer_classes = (JSONRenderer,)

    def prepare_groups(self, groups):

        prepared_groups = {}

        for name_uuid, data in groups.items():

            taxon = {
                'name_uuid': name_uuid,
                'taxon_source': data['taxon_source'],
                'taxon_latname': data['taxon_latname'],
                'taxon_author': data['taxon_author'],
                'taxon_nuid': data['taxon_nuid'],
            }

            prepared_groups[name_uuid] = {
                'count': data['count'],
                'taxon': taxon,
            }

        return prepared_groups
