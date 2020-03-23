from rest_framework import serializers
from django.contrib.auth import get_user_model

from localcosmos_server.datasets.models import Dataset, DatasetImages

from django_road.serializer_fields import RemoteDBJSONField

User = get_user_model()


class LocalcosmosUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        exclude = ('password',)


'''
    The Dataset is stored using the RemoteDB interface of the webapp
    OR by using the sync button on the native app
'''
class DatasetSerializer(serializers.ModelSerializer):

    assign_authenticated_user = 'user' # assigns the authenticated user to the field user on insert and update

    data = RemoteDBJSONField(binary=True)
    created_at = serializers.DateTimeField()
    last_modified = serializers.DateTimeField(required=False)

    # SerializerMethodFields are only for to_representation
    thumbnail = serializers.SerializerMethodField()

    user = LocalcosmosUserSerializer(many=False, read_only=True)

    def get_thumbnail(self, obj):

        image = DatasetImages.objects.filter(dataset=obj).first()
        
        if image:
            # App clients need the full url
            relative_url = image.thumbnail(size=200)
            url = '{0}://{1}{2}'.format(self.request.scheme, self.request.get_host(), relative_url)
            return url
        
        return None


    class Meta:
        model = Dataset
        fields = ('__all__')
        read_only_fields = ('user_id', 'client_id')


'''
    DatasetImagesSerializer
    - keep thumbnails in sync with [App][models.js].DatasetImages.fields.image.thumbnails
'''
APP_THUMBNAILS = {
    "small" : {
        "size" : [100, 100],
        "type" : "cover"
    }, 
    "medium" : {
        "size" : [400, 400],
        "type" : "cover"
    },
    "full_hd" : {
        "size" : [1920, 1080],
        "type" : "contain"
    }
}

class FlexImageField(serializers.ImageField):

    def to_representation(self, image):

        dataset_image = image.instance

        host = '{0}://{1}'.format(self.parent.request.scheme, self.parent.request.get_host())

        relative_url = image.url
        url = '{0}{1}'.format(host,relative_url)
        
        fleximage = {
            'url' : url,
        }

        for name, definition in APP_THUMBNAILS.items():

            if definition['type'] == 'cover':
                 relative_thumb_url = dataset_image.thumbnail(definition['size'][0])

            else:
                relative_thumb_url = dataset_image.resized(name, max_size=definition['size'])

            thumb_url = '{0}{1}'.format(host, relative_thumb_url)
            fleximage[name] = thumb_url

        return fleximage


'''
    return the DatasetImages.Dataset as a serialized Dataset
'''
class DatasetField(serializers.PrimaryKeyRelatedField):

    def to_representation(self, value):
        data = {
            'id' : value.pk
        }

        return data
        

class DatasetImagesSerializer(serializers.ModelSerializer):

    # there is only 1 FK
    serializer_related_field = DatasetField

    class Meta:
        model = DatasetImages
        fields = ('__all__')

from django.db.models import ImageField
DatasetImagesSerializer.serializer_field_mapping[ImageField] = FlexImageField
