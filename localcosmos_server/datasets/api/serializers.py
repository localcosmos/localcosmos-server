from rest_framework import serializers

from django.contrib.auth import get_user_model

from localcosmos_server.datasets.models import ObservationForm, Dataset, DatasetImages


from localcosmos_server.api.serializers import LocalcosmosUserSerializer
from localcosmos_server.api.serializer_fields import FlexImageField

from django.utils.translation import gettext_lazy as _

import jsonschema


User = get_user_model()


'''
    ObservationForms
'''
class ObservationFormSerializer(serializers.Serializer):

    definition = serializers.JSONField()

    # validate the observation form according to the jsonschema
    def validate_definition(self, value):

        try:
            is_valid = jsonschema.validate(value, ObservationForm.get_json_schema())
        except jsonschema.exceptions.ValidationError as e:
            raise serializers.ValidationError(e.message)
        return value


    def create(self, validated_data):
        
        observation_form_json = validated_data['definition']
        observation_form_uuid = observation_form_json['uuid']
        version = observation_form_json['version']

        observation_form = ObservationForm.objects.filter(uuid=observation_form_uuid, version=version).first()

        if not observation_form:

            observation_form = ObservationForm(
                uuid=observation_form_uuid,
                version=version,
                definition = observation_form_json,
            )

            observation_form.save()

        return observation_form


    def to_representation(self, instance):
        ret = super().to_representation(instance)
        return ret['definition']


'''
    Datasets
'''
class DatasetSerializer(serializers.Serializer):

    uuid = serializers.UUIDField(read_only=True)

    observation_form_uuid = serializers.UUIDField(source='observation_form.uuid')
    observation_form_version = serializers.IntegerField(source='observation_form.version')
    
    data = serializers.JSONField()

    client_id = serializers.CharField()
    platform = serializers.CharField()

    created_at = serializers.DateTimeField()
    last_modified = serializers.DateTimeField(required=False)

    # SerializerMethodFields are only for to_representation
    #thumbnail = serializers.SerializerMethodField()

    user = LocalcosmosUserSerializer(many=False, read_only=True, allow_null=True)

    
    def __init__(self, app_uuid, *args, **kwargs):
        self.app_uuid = app_uuid
        super().__init__(*args, **kwargs)

    '''
    def get_thumbnail(self, obj):

        image = DatasetImages.objects.filter(dataset=obj).first()
        
        if image:
            # App clients need the full url
            relative_url = image.thumbnail(size=200)
            url = '{0}://{1}{2}'.format(self.request.scheme, self.request.get_host(), relative_url)
            return url
        
        return None
    '''

    def validate(self, data):
        
        observation_form_uuid = data['observation_form']['uuid']
        observation_form_version = data['observation_form']['version']
        
        observation_form = ObservationForm.objects.filter(uuid=observation_form_uuid,
            version=observation_form_version).first()

        if not observation_form:
            raise serializers.ValidationError(_('Observation Form does not exist'))

        return data


    def create(self, validated_data):

        observation_form = ObservationForm.objects.get(uuid=validated_data['observation_form']['uuid'],
            version=validated_data['observation_form']['version'])

        dataset = Dataset(
            app_uuid = self.app_uuid,
            observation_form = observation_form,
            client_id = validated_data['client_id'],
            platform = validated_data['platform'],
            data = validated_data['data'],
            created_at = validated_data['created_at'],
            user = validated_data.get('user', None),
        )

        dataset.save()

        return dataset


    def update (self, instance, validated_data):


        if str(instance.observation_form.uuid) == str(validated_data['observation_form']['uuid']) and instance.observation_form.version == validated_data['observation_form']['version']:
            
            instance.data = validated_data['data']
            instance.save()

        else:
            raise ValueError('Changing the Observation Form of a dataset is not supported')

        return instance
    


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