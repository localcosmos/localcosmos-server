from rest_framework import generics, status
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response

from .serializers import (DatasetSerializer, ObservationFormSerializer, DatasetListSerializer, DatasetImagesSerializer,
                          UserGeometrySerializer, DatasetFilterSerializer)

from .permissions import (AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly, AuthenticatedOwnerOnly,
                          AnonymousObservationsPermissionOrGet, MaxThreeInstancesPerUser)

from localcosmos_server.api.permissions import AppMustExist
from localcosmos_server.api.views import SchemaSpecificMapClusterer

from localcosmos_server.datasets.models import Dataset, ObservationForm, DatasetImages, UserGeometry

from djangorestframework_camel_case.parser import CamelCaseJSONParser, CamelCaseMultiPartParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample, OpenApiParameter

from .examples import get_observation_form_example


@extend_schema_view(
    post=extend_schema(
        examples=[
            OpenApiExample(
                'Observation Form',
                description='observation form with all possible fields',
                value={'definition': get_observation_form_example()}
            ),
        ],
    )
)
class CreateObservationForm(generics.CreateAPIView):

    serializer_class = ObservationFormSerializer
    permission_classes = (AppMustExist, AnonymousObservationsPermission,)
    parser_classes = (CamelCaseJSONParser,)


@extend_schema_view(
    get=extend_schema(
        examples=[
            OpenApiExample(
                'Observation Form',
                description='observation form with all possible fields',
                value={'definition': get_observation_form_example()}
            ),
        ]
    )
)
class RetrieveObservationForm(generics.RetrieveAPIView):

    serializer_class = ObservationFormSerializer
    permission_classes = (AnonymousObservationsPermissionOrGet,)
    parser_classes = (CamelCaseJSONParser,)

    queryset = ObservationForm.objects.all()

    def get_object(self):

        queryset = self.filter_queryset(self.get_queryset())

        filter_kwargs = {
            'uuid': self.kwargs['observation_form_uuid'],
            'version': self.kwargs['version']
        }
        obj = generics.get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class AppUUIDSerializerMixin:

    def get_serializer(self, *args, **kwargs):

        import uuid

        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())

        if getattr(self, 'swagger_fake_view', False):  # drf-yasg comp
            app_uuid = str(uuid.uuid4())
            self.kwargs['app_uuid'] = app_uuid

        return serializer_class(self.kwargs['app_uuid'], *args, **kwargs)


'''
    Retrieve multiple Datasets or Create one Dataset
    The GET endpoint is only for simple lookups:
    - retrieve all datasets for the logged in user (GET)
    - retrieve all datasets for one client_id (GET)
    - retrieve all datasets (GET)
    - more complex lookups require a separate POST endpoint with filters as JSON
'''
class ListCreateDataset(AppUUIDSerializerMixin, generics.ListCreateAPIView):

    permission_classes = (AppMustExist, AnonymousObservationsPermissionOrGet,)
    authentication_classes = (JWTAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def perform_create(self, serializer):

        if self.request.user.is_authenticated == True:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def get_queryset(self):
        queryset = Dataset.objects.filter(app_uuid=self.kwargs['app_uuid'])

        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
        elif 'client_id' in self.request.GET:
            queryset = queryset.filter(client_id=self.request.GET['client_id'])

        return queryset

    def get_serializer(self, *args, **kwargs):

        import uuid

        kwargs.setdefault('context', self.get_serializer_context())

        if getattr(self, 'swagger_fake_view', False):  # drf-yasg comp
            app_uuid = str(uuid.uuid4())
            self.kwargs['app_uuid'] = app_uuid

        if self.request.method == 'GET':
            return DatasetListSerializer(*args, **kwargs)

        return DatasetSerializer(self.kwargs['app_uuid'], *args, **kwargs)


class GetFilteredDatasets(generics.ListAPIView):
    permission_classes = (AppMustExist,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = DatasetListSerializer
    filter_serializer = DatasetFilterSerializer

    def get_queryset(self, filters=[], order_by=None):
        queryset = Dataset.objects.filter(app_uuid=self.app_uuid)

        orm_filters = {}
        orm_excludes = {}
        for filter in filters:
            operator = filter['operator']

            if operator == '=':
                orm_filters[filter['column']] = filter['value']
            elif operator == '!=':
                orm_excludes[filter['column']] = filter['value']
            elif operator == 'startswith':
                column = '{0}__istartswith'.format(filter['column'])
                orm_filters[column] = filter['value']

        queryset = queryset.filter(**orm_filters).exclude(**orm_excludes)

        if order_by:
            queryset = queryset.order_by(order_by)

        return queryset


    def post(self, request, *args, **kwargs):

        self.app_uuid = kwargs['app_uuid']

        filter_serializer = self.filter_serializer(data=request.data)

        if filter_serializer.is_valid():

            filters = filter_serializer.validated_data.get('filters', [])
            order_by = filter_serializer.validated_data.get('order_by', None)

            queryset = self.get_queryset(filters, order_by)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManageDataset(AppUUIDSerializerMixin, generics.RetrieveUpdateDestroyAPIView):

    lookup_field = 'uuid'

    serializer_class = DatasetSerializer
    permission_classes = (
        AppMustExist, AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly)
    parser_classes = (CamelCaseJSONParser,)

    queryset = Dataset.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        return [permission() for permission in self.permission_classes]


class CreateDatasetImage(generics.CreateAPIView):

    serializer_class = DatasetImagesSerializer
    permission_classes = (
        AppMustExist, AnonymousObservationsPermission, DatasetOwnerOnly)
    parser_classes = (CamelCaseMultiPartParser,)

    def create(self, request, *args, **kwargs):

        dataset = Dataset.objects.get(uuid=kwargs['uuid'])

        request.data['dataset'] = str(dataset.uuid)

        return super().create(request, *args, **kwargs)


class DestroyDatasetImage(AppUUIDSerializerMixin, generics.DestroyAPIView):

    serializer_class = DatasetSerializer
    permission_classes = (
        AppMustExist, AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly)
    parser_classes = (CamelCaseJSONParser,)

    queryset = DatasetImages.objects.all()


class CreateListUserGeometry(generics.ListCreateAPIView):

    queryset = UserGeometry.objects.all()
    serializer_class = UserGeometrySerializer
    permission_classes = (AppMustExist, IsAuthenticated,
                          MaxThreeInstancesPerUser)
    parser_classes = (CamelCaseJSONParser,)


class ManageUserGeometry(generics.RetrieveDestroyAPIView):

    queryset = UserGeometry.objects.all()
    serializer_class = UserGeometrySerializer
    permission_classes = (AppMustExist, AuthenticatedOwnerOnly)
    parser_classes = (CamelCaseJSONParser,)
