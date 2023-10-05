from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model

from localcosmos_server.datasets.models import ObservationForm, Dataset, DatasetImages, UserGeometry

from localcosmos_server.datasets.json_schemas import (POINT_JSON_FIELD_SCHEMA, GEOJSON_FIELD_SCHEMA,
    TEMPORAL_JSON_FIELD_SCHEMA, TAXON_JSON_SCHEMA)

from localcosmos_server.datasets.api.serializer_fields import GeoJSONField

from localcosmos_server.api.serializers import LocalcosmosPublicUserSerializer

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

import json, jsonschema


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



@extend_schema_field(OpenApiTypes.OBJECT)
class ObservationFormField(serializers.Field):

    default_error_messages = {
        'invalid': _('Invalid observation form given.')
    }

    def to_internal_value(self, data):

        if not isinstance(data, dict) or 'version' not in data or 'uuid' not in data:
            self.fail('invalid')
        
        return data

    def to_representation(self, value):
        data = {
            'uuid' : str(value.uuid),
            'version': value.version,
        }

        return data
        


class UUIDRelatedField(serializers.RelatedField):

    default_error_messages = {
        'does_not_exist': _('Object with uuid={value} does not exist.'),
        'invalid': _('Invalid value.'),
    }

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            return queryset.get(**{'uuid': data})
        except ObjectDoesNotExist:
            self.fail('does_not_exist', value=str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return str(getattr(obj, 'uuid'))


class DatasetImagesSerializer(serializers.ModelSerializer):

    dataset = UUIDRelatedField(
        many=False,
        queryset=Dataset.objects.all()
     )

    image_url = serializers.SerializerMethodField()

    client_id = serializers.SerializerMethodField()

    def get_image_url(self, instance):
        if ('request' in self.context):
            image_urls = instance.image_urls(self.context['request'])
        else:
            image_urls = instance.image_urls()
            
        return image_urls

    def get_client_id(self, instance):
        return instance.client_id

    class Meta:
        model = DatasetImages
        fields = ['id', 'dataset', 'field_uuid', 'image', 'image_url', 'client_id']


'''
    Datasets
'''
class DatasetImagesMixin:

    def get_images(self, obj):

        images = DatasetImages.objects.filter(dataset=obj)

        serialized_images = {}

        for image in images:
            field_uuid = str(image.field_uuid)
            if field_uuid not in serialized_images:
                serialized_images[field_uuid] = []
            serializer = DatasetImagesSerializer(image, context=self.context)
            serialized_images[field_uuid].append(serializer.data)
        
        return serialized_images

# Retrieve works without app_uuid in __init__ and is compatible with anycluster
class DatasetRetrieveSerializer(DatasetImagesMixin, serializers.Serializer):

    uuid = serializers.UUIDField(read_only=True)

    observation_form = ObservationFormField()
    
    data = serializers.JSONField()

    client_id = serializers.CharField(write_only=True)
    platform = serializers.CharField(write_only=True)

    #created_at = serializers.DateTimeField(required=False)
    #last_modified = serializers.DateTimeField(required=False)

    coordinates = serializers.SerializerMethodField()

    timestamp = serializers.DateTimeField(read_only=True)

    taxon_source = serializers.CharField(read_only=True)
    taxon_latname = serializers.CharField(read_only=True)
    taxon_author = serializers.CharField(read_only=True)
    name_uuid = serializers.CharField(read_only=True)
    taxon_nuid = serializers.CharField(read_only=True)

    images = serializers.SerializerMethodField(read_only=True) #DatasetImagesSerializer(many=True, read_only=True)

    user = LocalcosmosPublicUserSerializer(many=False, read_only=True, allow_null=True)

    validation_step = serializers.CharField(read_only=True)


    def get_observation_form(self, data):
        observation_form_uuid = data['observation_form']['uuid']
        observation_form_version = data['observation_form']['version']
        
        observation_form = ObservationForm.objects.filter(uuid=observation_form_uuid,
            version=observation_form_version).first()

        return observation_form

    # always return lng lat Point
    def get_coordinates(self, obj):
        coordinates = None
        if obj.coordinates:
            coordinates = {
                "type": "Feature",
                "geometry": json.loads(obj.coordinates.geojson),
            }
        return coordinates
    

class DatasetSerializer(DatasetRetrieveSerializer):
    
    def __init__(self, app_uuid, *args, **kwargs):
        self.app_uuid = app_uuid
        super().__init__(*args, **kwargs)

    
    def validate(self, data):

        observation_form = self.get_observation_form(data)

        if not observation_form:
            raise serializers.ValidationError(_('Observation Form does not exist'))

        # check if required fields are missing in data
        for generic_form_field in observation_form.definition['fields']:
            if generic_form_field['definition']['required']:
                required_uuid = generic_form_field['uuid']
                if required_uuid not in data['data']:
                    message = self.get_required_field_error_message(generic_form_field)
                    error = {}
                    error[required_uuid] = [message]
                    raise serializers.ValidationError(error)


        for field_uuid, value in data['data'].items():

            field = None
            for _field in observation_form.definition['fields']:
                if _field['uuid'] == field_uuid:
                    field = _field
                    break
            
            if not field:
                raise serializers.ValidationError(_('Invalid field uuid: %(field_uuid)s') % {'field_uuid': field_uuid})

            required = field['definition']['required']
            if required == True and value is None:
                message = self.get_required_field_error_message(field)
                raise serializers.ValidationError(message)
        
            else:
                validator_name = 'validate_{0}'.format(field['fieldClass'])
                validator = getattr(self, validator_name)
                value = validator(field, value)

        return data


    '''
        validate data according to the observation form
    '''
    def get_required_field_error_message(self, field):
        message = _('The field %(field_name)s is required.') % {'field_name': field['definition']['label']}
        return message

    def get_invalid_datatype_error_message(self, field):
        message = _('Invalid datatype for %(field_name)s.') % {'field_name': field['definition']['label'] }
        return message

    def validate_json_schema(self, value, schema):
        try:
            is_valid = jsonschema.validate(value, schema)
        except jsonschema.exceptions.ValidationError as e:
            raise serializers.ValidationError(e.message)
        return value

    def validate_PointJSONField(self, field, value):
        return self.validate_json_schema(value, POINT_JSON_FIELD_SCHEMA)

    def validate_GeoJSONField(self, field, value):
        return self.validate_json_schema(value, GEOJSON_FIELD_SCHEMA)

    # currently, only a timestamp with date, time and timezone is supported
    def validate_DateTimeJSONField(self, field, value):
        return self.validate_json_schema(value, TEMPORAL_JSON_FIELD_SCHEMA)

    def validate_TaxonField(self, field, value):
        return self.validate_json_schema(value, TAXON_JSON_SCHEMA)

    def validate_SelectTaxonField(self, field, value):
        return self.validate_TaxonField(field, value)
    
    def validate_CharField(self, field, value):
        required = field['definition']['required']
        if required == True and not value:
            message = self.get_required_field_error_message(field)
            raise serializers.ValidationError(message)
        return value


    # validatoin for number fields
    def validate_min_max(self, field, value):

        min = field['widgetAttrs'].get('min', None)
        max = field['widgetAttrs'].get('max', None)

        if min != None and value < min:
            message = _('Minimum value for %(field_name)s is %(min)s.') % {
                'field_name': field['definition']['label'],
                'min': str(min),
            }
            raise serializers.ValidationError(message)

        if max != None and value > max:
            message = _('Maximum value for %(field_name)s is %(max)s.') % {
                'field_name': field['definition']['label'],
                'min': str(max),
            }
            raise serializers.ValidationError(message)

        return value


    def validate_DecimalField(self, field, value):
        try:
            value = float(value)
        except Exception as e:
            message = self.get_invalid_datatype_error_message(field)
            raise serializers.ValidationError(message)

        value = self.validate_min_max(field, value)

        return value


    def validate_FloatField(self, field, value):
        return self.validate_DecimalField(field, value)


    def validate_IntegerField(self, field, value):
        if not isinstance(value, int):
            message = self.get_invalid_datatype_error_message(field)
            raise serializers.ValidationError(message)

        value = self.validate_min_max(field, value)

        return value


    def validate_BooleanField(self, field, value):
        if not isinstance(value, bool):
            message = self.get_invalid_datatype_error_message(field)
            raise serializers.ValidationError(message)

        return value


    def validate_PictureField(self, field, value):
        return value


    # validations for choice fields
    # check if the value is contained by the field choices
    def get_invalid_choice_error_message(self, field, value):
        message = _('Invalid choice for %(field_name)s: %(value)s') % {
            'field_name': field['definition']['label'],
            'value' : str(value),
        }

        return message

    def validate_ChoiceField(self, field, value):
        choices = [choice[0] for choice in field['definition']['choices']]
        if value not in choices:
            message = self.get_invalid_choice_error_message(field, value)
            raise serializers.ValidationError(message)
        return value

    def validate_MultipleChoiceField(self, field, value):

        if not isinstance(value, list):
            message = self.get_invalid_datatype_error_message(field)
            raise serializers.ValidationError(message)

        
        accepted_choices = [accepted_choice[0] for accepted_choice in field['definition']['choices']]

        for choice in value:
            if choice not in accepted_choices:
                message = self.get_invalid_choice_error_message(field, choice)
                raise serializers.ValidationError(message)

        return value


    def create(self, validated_data):

        observation_form = ObservationForm.objects.get(uuid=validated_data['observation_form']['uuid'],
            version=validated_data['observation_form']['version'])

        created_at = validated_data.get('created_at', timezone.now())

        dataset = Dataset(
            app_uuid = self.app_uuid,
            observation_form = observation_form,
            client_id = validated_data['client_id'],
            platform = validated_data['platform'],
            data = validated_data['data'],
            created_at = created_at,
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


class TaxonSerializer(serializers.Serializer):

    taxon_source = serializers.CharField()
    taxon_latname = serializers.CharField()
    taxon_author = serializers.CharField(required=False)
    taxon_nuid = serializers.CharField()
    name_uuid = serializers.CharField()



class DatasetListSerializer(serializers.ModelSerializer):

    taxon = serializers.SerializerMethodField()
    coordinates = GeoJSONField()
    geographic_reference = GeoJSONField()

    image_url = serializers.SerializerMethodField(read_only=True) #DatasetImagesSerializer(many=True, read_only=True)

    user = LocalcosmosPublicUserSerializer(many=False, read_only=True, allow_null=True)

    def get_taxon(self, instance):

        taxon = None
        
        if instance.taxon:
            serializer = TaxonSerializer(instance.taxon)
            taxon = serializer.data

        return taxon

    def get_image_url(self, obj):

        image = DatasetImages.objects.filter(dataset=obj).first()

        image_url = None

        serializer = DatasetImagesSerializer(image, context=self.context)
        if serializer.data and 'image_url' in serializer.data:
            image_url = serializer.data['image_url']
        return image_url

    class Meta:
        model = Dataset
        fields = ('uuid', 'taxon', 'coordinates', 'geographic_reference', 'timestamp', 'image_url', 'user', 'validation_step',
            'is_valid', 'is_published')





class UserGeometrySerializer(serializers.ModelSerializer):

    geometry = GeoJSONField()

    def create(self, validated_data):
        user_geometry = UserGeometry.objects.create(
            user=self.context['request'].user,
            **validated_data
        )
        return user_geometry

    class Meta:
        model = UserGeometry
        fields = ('id', 'geometry', 'name')