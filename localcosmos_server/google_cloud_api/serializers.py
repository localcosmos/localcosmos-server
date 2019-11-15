from rest_framework import serializers


class ImageSerializer(serializers.Serializer):
    image = serializers.ImageField(allow_empty_file=False, required=True)
