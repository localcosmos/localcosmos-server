from rest_framework.generics import GenericAPIView
from rest_framework import mixins

from localcosmos_server.template_content.models import LocalizedTemplateContent


from .serializers import LocalizedTemplateContentSerializer

class GetTemplateContentCommon:

    queryset = LocalizedTemplateContent.objects.all()
    serializer_class = LocalizedTemplateContentSerializer
    lookup_url_kwarg = 'slug'
    lookup_field = 'slug'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class GetTemplateContent(GetTemplateContentCommon, mixins.RetrieveModelMixin, GenericAPIView):

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['preview'] = False
        return context


class GetTemplateContentPreview(GetTemplateContentCommon, mixins.RetrieveModelMixin, GenericAPIView):

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['preview'] = True
        return context
