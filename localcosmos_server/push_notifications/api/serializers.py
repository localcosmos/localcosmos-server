from rest_framework import serializers

class RegisterFCMDeviceSerializer(serializers.Serializer):
    registration_id = serializers.CharField()
    type = serializers.ChoiceField(choices=['android', 'ios', 'browser'])
    client_id = serializers.CharField()
    language_code = serializers.CharField(max_length=15, required=False, default='', allow_blank=True)
    
class DeregisterFCMDeviceSerializer(serializers.Serializer):
    client_id = serializers.CharField()