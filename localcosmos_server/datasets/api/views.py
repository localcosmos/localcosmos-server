from rest_framework import generics, mixins

from rest_framework.permissions import IsAuthenticated

from .serializers import (DatasetSerializer, ObservationFormSerializer, DatasetListSerializer, DatasetImagesSerializer,
                            UserGeometrySerializer)
from .permissions import (AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly, AuthenticatedOwnerOnly,
                            AnonymousObservationsPermissionOrGet, MaxThreeInstancesPerUser)

from localcosmos_server.api.permissions import AppMustExist

from localcosmos_server.datasets.models import Dataset, ObservationForm, DatasetImages, UserGeometry

from djangorestframework_camel_case.parser import CamelCaseJSONParser, CamelCaseMultiPartParser

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample, OpenApiParameter

from .examples import get_observation_form_example

import uuid


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
    permission_classes = (AnonymousObservationsPermission,)
    parser_classes = (CamelCaseJSONParser,)

    queryset = ObservationForm.objects.all()

    def get_object(self):

        queryset = self.filter_queryset(self.get_queryset())

        filter_kwargs = {
            'uuid' : self.kwargs['observation_form_uuid'],
            'version' : self.kwargs['version']
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



class ListCreateDataset(AppUUIDSerializerMixin, generics.ListCreateAPIView):
    
    permission_classes = (AppMustExist, AnonymousObservationsPermissionOrGet,)
    parser_classes = (CamelCaseJSONParser,)

    def perform_create(self, serializer):

        if self.request.user.is_authenticated == True:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def get_queryset(self):
        queryset = Dataset.objects.filter(app_uuid=self.kwargs['app_uuid'])
        
        if self.request.user.is_authenticated:
            queryset=queryset.filter(user=self.request.user)
        elif 'client_id' in self.request.GET:
            queryset=queryset.filter(client_id=self.request.GET['client_id'])
        else:
            queryset = Dataset.objects.none()
        
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


class ManageDataset(AppUUIDSerializerMixin, generics.RetrieveUpdateDestroyAPIView):

    lookup_field = 'uuid'
    
    serializer_class = DatasetSerializer
    permission_classes = (AppMustExist, AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly)
    parser_classes = (CamelCaseJSONParser,)

    queryset = Dataset.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        return [permission() for permission in self.permission_classes]



class CreateDatasetImage(generics.CreateAPIView):

    serializer_class = DatasetImagesSerializer
    permission_classes = (AppMustExist, AnonymousObservationsPermission, DatasetOwnerOnly)
    parser_classes = (CamelCaseMultiPartParser,)

    def create(self, request, *args, **kwargs):

        dataset = Dataset.objects.get(uuid=kwargs['uuid'])

        request.data['dataset'] = str(dataset.uuid)
        
        return super().create(request, *args, **kwargs)


class DestroyDatasetImage(AppUUIDSerializerMixin, generics.DestroyAPIView):
    
    serializer_class = DatasetSerializer
    permission_classes = (AppMustExist, AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly)
    parser_classes = (CamelCaseJSONParser,)

    queryset = DatasetImages.objects.all()


class CreateListUserGeometry(generics.ListCreateAPIView):

    queryset = UserGeometry.objects.all()
    serializer_class = UserGeometrySerializer
    permission_classes = (AppMustExist, IsAuthenticated, MaxThreeInstancesPerUser)
    parser_classes = (CamelCaseJSONParser,)
    

class ManageUserGeometry(generics.RetrieveDestroyAPIView):

    queryset = UserGeometry.objects.all()
    serializer_class = UserGeometrySerializer
    permission_classes = (AppMustExist, AuthenticatedOwnerOnly)
    parser_classes = (CamelCaseJSONParser,)
