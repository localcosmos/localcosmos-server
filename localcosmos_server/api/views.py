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
from rest_framework import serializers

#from drf_spectacular.utils import inline_serializer, extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from rest_framework import status

from localcosmos_server.models import App, ServerContentImage, LocalcosmosUser

from localcosmos_server.taxonomy.lazy import LazyAppTaxon


from .serializers import (LocalcosmosUserSerializer, RegistrationSerializer, PasswordResetSerializer,
                            TokenObtainPairSerializerWithClientID, ServerContentImageSerializer,
                            LocalcosmosPublicUserSerializer, ContactUserSerializer, TaxonProfileSerializer,
                            TaxonProfileMinimalSerializer)

from .permissions import OwnerOnly, AppMustExist, ServerContentImageOwnerOrReadOnly

from localcosmos_server.mails import (send_registration_confirmation_email, send_user_contact_email)

from localcosmos_server.datasets.models import Dataset
from localcosmos_server.models import UserClients

from djangorestframework_camel_case.parser import CamelCaseJSONParser, CamelCaseMultiPartParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer, extend_schema_view, OpenApiExample, OpenApiParameter


from .examples import get_taxon_profile_example

import os
import json

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



class GetUserProfile(generics.RetrieveAPIView):
    serializer_class = LocalcosmosPublicUserSerializer
    renderer_classes = (CamelCaseJSONRenderer,)
    parser_classes = (CamelCaseJSONParser,)
    permission_classes = ()

    lookup_field = 'uuid'
    lookup_url_kwargs = 'uuid'

    queryset = LocalcosmosUser.objects.all()
    
    
    
class ContactUser(APIView):
    '''
        Contact a user
        - authenticated users only
        - contected user user gets mail
        - contectee does not get an email
        - [POST] delivers an email to the user
    '''

    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = ContactUserSerializer

    def post(self, request, *args, **kwargs):

        # permission checks, raises 404s
        sending_user = self.request.user

        receiving_user = LocalcosmosUser.objects.filter(uuid=kwargs['user_uuid']).first()

        if not receiving_user:
            return Response('', status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            # send mail
            send_user_contact_email(kwargs['app_uuid'], sending_user, receiving_user,
                                    serializer.data['subject'], serializer.data['message'])
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

###################################################################################################################
#
#   Taxon Profile API ENDPOINTS
#   - app specific
#   - authenticatoin required
#   - taxon profiles are read from json files in the app's data directory
####################################################################################################################
class AppAPIViewMixin:
    
    def get_on_disk_path(self, relative_path):
        """
        Returns the absolute path to a file or directory within the app's root directory.
        """
        if not hasattr(self, 'app_root'):
            raise ValueError("App root is not set. Call load_app() first.")
        return os.path.join(self.app_root, relative_path.lstrip('/'))
    
    def load_app(self, app_uuid):
        try:
            app = App.objects.get(uuid=app_uuid)
        except App.DoesNotExist:
            raise Http404(_('App not found.'))

        self.app = app
        self.app_settings = app.get_settings('published')
        self.app_features = app.get_features('published')
        self.app_root = app.get_installed_app_path('published')
    
    def dispatch(self, request, *args, **kwargs):
        app_uuid = kwargs.get('app_uuid')
        if not app_uuid:
            raise Http404(_('App UUID is required.'))
        self.load_app(app_uuid)
        self.request_language = request.GET.get('language', self.app.primary_language)
        response = super().dispatch(request, *args, **kwargs)
        return response


class TaxonProfilesAPIViewMixin(AppAPIViewMixin):
    
    def get_id_to_taxon_map(self):
        
        taxon_profiles_feature = self.app_features['TaxonProfiles']
        id_to_taxon_map_relative_path = taxon_profiles_feature['idToTaxonMap']
        id_to_taxon_map_path = self.get_on_disk_path(id_to_taxon_map_relative_path)

        with open(id_to_taxon_map_path, 'r') as f:
            id_to_taxon_map = json.load(f)
            
        return id_to_taxon_map
    
    def get_app_taxon_profile_json_from_taxon(self, lazy_taxon):
        
        taxon_profiles_feature = self.app_features['TaxonProfiles']
        localized_files = taxon_profiles_feature['localizedFiles']
        
        localized_folder = localized_files.get(self.request_language)
        if localized_folder:
            localized_folder_path = self.get_on_disk_path(localized_folder)
            taxon_profiles_json_path = os.path.join(localized_folder_path, lazy_taxon.taxon_source, '{0}.json'.format(lazy_taxon.name_uuid))
            
            if os.path.isfile(taxon_profiles_json_path):
                try:
                    with open(taxon_profiles_json_path, 'r') as f:
                        taxon_profile = json.load(f)
                    return taxon_profile
                except FileNotFoundError:
                    return None
                except json.JSONDecodeError:
                    return None
        return None

    def get_app_taxon_profile_from_id(self, pk):
        
        id_to_taxon_map = self.get_id_to_taxon_map()
        
        taxon = id_to_taxon_map.get(str(pk))
        if not taxon:
            return None
        
        lazy_taxon = LazyAppTaxon(**taxon)
        
        taxon_profile = self.get_app_taxon_profile_json_from_taxon(lazy_taxon)
        
        if taxon_profile is None:
            return None
        
        return taxon_profile


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                name='page',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Page number (starts at 1)'
            ),
            OpenApiParameter(
                name='page_size',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Number of items per page (default 20, max 50)'
            ),
        ],
        responses=inline_serializer(
            name='PaginatedTaxonProfileList',
            fields={
                'count': serializers.IntegerField(),
                'page': serializers.IntegerField(),
                'page_size': serializers.IntegerField(),
                'results': TaxonProfileSerializer(many=True),
            }
        ),
        examples=[
            OpenApiExample(
                'Taxon Profile List',
                description='A paginated list of taxon profiles',
                value={
                    'count': 1,
                    'page': 1,
                    'page_size': 20,
                    'results': [get_taxon_profile_example()]
                }
            )
        ]
    )
)
class TaxonProfileList(TaxonProfilesAPIViewMixin, APIView):
    permission_classes = (AppMustExist,)
    serializer_class = TaxonProfileSerializer
    
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 50

    def get(self, request, *args, **kwargs):
        
        id_to_taxon_map = self.get_id_to_taxon_map()
        
        # sort the dictionary by key
        sorted_taxa = sorted(id_to_taxon_map.items(), key=lambda item: item[0])
        
        sorted_taxon_profile_ids = [t[0] for t in sorted_taxa]
        
        # Pagination logic
        try:
            page_size = int(request.GET.get('page_size', self.DEFAULT_PAGE_SIZE))
        except ValueError:
            page_size = self.DEFAULT_PAGE_SIZE
        page_size = min(page_size, self.MAX_PAGE_SIZE)

        try:
            page = int(request.GET.get('page', 1))
        except ValueError:
            page = 1
        page = max(page, 1)
        
        # get the id batch according to the page
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paged_taxon_profile_ids = sorted_taxon_profile_ids[start_index:end_index]
        
        taxon_profiles = []
        for taxon_profile_id in paged_taxon_profile_ids:
            taxon_profile = self.get_app_taxon_profile_from_id(taxon_profile_id)
            if taxon_profile is not None:
                serializer = self.serializer_class(taxon_profile, app=self.app)
                taxon_profiles.append(serializer.data)

        response_data = {
            'count': len(taxon_profiles),
            'page': page,
            'page_size': page_size,
            'results': taxon_profiles,
        }
        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        responses = TaxonProfileSerializer,
        examples = [
            OpenApiExample(
                'Taxon Profile',
                description='A Taxon Profile',
                value=get_taxon_profile_example(),
            )
        ]
    )
)
class TaxonProfileDetail(TaxonProfilesAPIViewMixin, APIView):
    permission_classes = (AppMustExist,)
    serializer_class = TaxonProfileSerializer

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        profile = self.get_app_taxon_profile_from_id(pk)
        if profile is None:
            return Response({'detail': 'Taxon profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(profile, app=self.app)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

@extend_schema_view(
    get=extend_schema(
        responses = TaxonProfileMinimalSerializer(many=True),
        examples = [
            OpenApiExample(
                'All Taxon Profiles',
                description='A list of all Taxon Profiles',
                value=[
                    {
                        'taxonProfileId': 1,
                        'taxonLatname': 'Abies alba',
                        'taxonAuthor': 'Mill.',
                        'vernacular': {
                            'de': 'Weisstanne'
                        }
                    }
                ]
            )
        ]
    )
)
class AllTaxonProfiles(TaxonProfilesAPIViewMixin, APIView):
    
    permission_classes = (AppMustExist,)
    serializer_class = TaxonProfileMinimalSerializer
    
    def get(self, request, *args, **kwargs):
        
        id_to_taxon_map = self.get_id_to_taxon_map()
        
        # sort the dictionary by key
        sorted_taxa = sorted(id_to_taxon_map.items(), key=lambda item: item[0])
        
        sorted_taxon_profile_ids = [t[0] for t in sorted_taxa]
        
        taxon_profiles = []
        for taxon_profile_id in sorted_taxon_profile_ids:
            taxon_profile = self.get_app_taxon_profile_from_id(taxon_profile_id)
            if taxon_profile is not None:
                serializer = self.serializer_class(taxon_profile, app=self.app)
                taxon_profiles.append(serializer.data)

        response_data = taxon_profiles
        
        return Response(response_data, status=status.HTTP_200_OK)
    

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
    renderer_classes = (CamelCaseJSONRenderer,)

class SchemaKmeansCluster(SchemaSpecificMapClusterer, KmeansCluster):
    parser_classes = (JSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

class SchemaGetClusterContent(SchemaSpecificMapClusterer, GetClusterContent):
    parser_classes = (JSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

# the client expects imageUrl, not image_url
class SchemaGetAreaContent(SchemaSpecificMapClusterer, GetAreaContent):
    parser_classes = (JSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

class SchemaGetDatasetContent(SchemaSpecificMapClusterer, GetDatasetContent):
    parser_classes = (JSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

class SchemaGetMapContentCount(SchemaSpecificMapClusterer, GetMapContentCount):
    parser_classes = (JSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

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
