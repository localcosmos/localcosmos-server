from rest_framework import serializers

from localcosmos_server.models import App
from localcosmos_server.analytics.models import AnonymousLog


class AppUUIDSerializer:
    def __init__(self, app_uuid, *args, **kwargs):
        self.app = App.objects.get(uuid=app_uuid)
        super().__init__(*args, **kwargs)


class AnonymousLogSerializer(AppUUIDSerializer, serializers.ModelSerializer):

    def create(self, validated_data):
       validated_data['app'] = self.app
       return super().create(validated_data)

    class Meta:
        model = AnonymousLog
        exclude = ('app',)


'''
    Retrieving only
'''
class EventCountSerializer(serializers.Serializer):
    
    event_type = serializers.CharField()
    event_content = serializers.CharField(required=False, read_only=True)
    count = serializers.IntegerField(read_only=True)
