from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from localcosmos_server.models import App

from localcosmos_server.api.permissions import AppMustExist
from localcosmos_server.datasets.api.views import AppUUIDSerializerMixin

from localcosmos_server.analytics.models import AnonymousLog

from .serializers import AnonymousLogSerializer, EventCountSerializer

class CreateAnonymousLogEntry(AppUUIDSerializerMixin, generics.CreateAPIView):
    permission_classes = (AppMustExist,)
    serializer_class = AnonymousLogSerializer
    parser_classes = (CamelCaseJSONParser,)


class EventCount:
    def __init__(self, event_type, count, event_content=None):
        self.event_type = event_type
        self.count = count
        self.event_content = event_content


class GetEventCounts(AppUUIDSerializerMixin, APIView):

    permission_classes = (AppMustExist,)
    serializer_class = EventCountSerializer
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get_queryset(self):
        app = App.objects.get(uuid=self.kwargs['app_uuid'])
        queryset = AnonymousLog.objects.filter(app=app)
        event_type = self.request.query_params.get('event-type')
        if event_type is not None:
            queryset = queryset.filter(event_type=event_type)

        event_content = self.request.query_params.get('event-content')
        if event_content is not None:
            queryset = queryset.filter(event_content=event_content)
        return queryset
    

    def get(self, request, *args, **kwargs):

        event_type = request.query_params.get('event-type')
        event_content = self.request.query_params.get('event-content')

        data = {
            'event_type': event_type,
            'event_content': event_content,
        }

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            queryset = self.get_queryset()
            count = queryset.count()

            event_count = EventCount(event_type, count, event_content=event_content)

            output_serializer = self.serializer_class(event_count)
            return Response(output_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
    