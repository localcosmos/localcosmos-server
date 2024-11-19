from rest_framework.generics import GenericAPIView
from rest_framework import mixins

from localcosmos_server.template_content.models import LocalizedTemplateContent, LocalizedNavigation
from localcosmos_server.models import App

from .serializers import LocalizedTemplateContentSerializer, LocalizedNavigationSerializer

class GetTemplateContentCommon:

    serializer_class = LocalizedTemplateContentSerializer
    lookup_url_kwarg = 'slug'
    lookup_field = 'slug'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        app = App.objects.get(uuid=self.kwargs['app_uuid'])
        queryset = queryset.filter(template_content__app=app)
        return queryset


class GetTemplateContent(GetTemplateContentCommon, mixins.RetrieveModelMixin, GenericAPIView):

    queryset = LocalizedTemplateContent.objects.filter(published_version__isnull=False)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['preview'] = False
        return context


class GetTemplateContentPreview(GetTemplateContentCommon, mixins.RetrieveModelMixin, GenericAPIView):

    queryset = LocalizedTemplateContent.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['preview'] = True
        return context


class GetNavigation(mixins.RetrieveModelMixin, GenericAPIView):
    
    serializer_class = LocalizedNavigationSerializer
    queryset = LocalizedNavigation.objects.filter(published_version__isnull=False)
    
    lookup_url_karg = 'language'
    lookup_field = 'language'
    
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['preview'] = False
        return context
    
    def get_queryset(self):
        queryset = super().get_queryset()
        app = App.objects.get(uuid=self.kwargs['app_uuid'])
        queryset = queryset.filter(navigation__app=app,
                                   navigation__navigation_type=self.kwargs['navigation_type'])
        return queryset


class GetNavigationPreview(GetNavigation, GenericAPIView):
    
    queryset = LocalizedNavigation.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['preview'] = True
        return context