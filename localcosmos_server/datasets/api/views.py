from rest_framework import generics

from .serializers import DatasetSerializer, ObservationFormSerializer
from .permissions import AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly
from localcosmos_server.api.permissions import AppMustExist

from localcosmos_server.datasets.models import Dataset, ObservationForm

from djangorestframework_camel_case.parser import CamelCaseJSONParser


class CreateObservationForm(generics.CreateAPIView):

    serializer_class = ObservationFormSerializer
    permission_classes = (AppMustExist, AnonymousObservationsPermission,)
    parser_classes = (CamelCaseJSONParser,)


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


class CreateDataset(AppUUIDSerializerMixin, generics.CreateAPIView):
    
    serializer_class = DatasetSerializer
    permission_classes = (AppMustExist, AnonymousObservationsPermission,)
    parser_classes = (CamelCaseJSONParser,)

    def perform_create(self, serializer):

        if self.request.user.is_authenticated == True:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class ManageDataset(AppUUIDSerializerMixin,generics.RetrieveUpdateDestroyAPIView):

    lookup_field = 'uuid'
    
    serializer_class = DatasetSerializer
    permission_classes = (AnonymousObservationsPermission, DatasetOwnerOnly, DatasetAppOnly)
    parser_classes = (CamelCaseJSONParser,)

    queryset = Dataset.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        return [permission() for permission in self.permission_classes]


'''
class DatasetList(AppUUIDSerializerMixin,generics.ListAPIView):

    serializer_class = DatasetSerializer
    parser_classes = (CamelCaseJSONParser,)
    permission_classes = []

    queryset = Dataset.objects.all()
'''
