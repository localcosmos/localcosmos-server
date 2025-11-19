from rest_framework import serializers

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

from localcosmos_server.models import ServerImageStore, ServerContentImage, EXTERNAL_MEDIA_TYPES

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import hashlib, json, os

class TokenObtainPairSerializerWithClientID(TokenObtainPairSerializer):

    # required for linking client_ids with users
    client_id = serializers.CharField()
    platform = serializers.CharField()

'''
    private user serializer: only accessible for the account owner
'''
class LocalcosmosUserSerializer(serializers.ModelSerializer):

    profile_picture = serializers.SerializerMethodField()

    def get_profile_picture(self, obj):
        content_image = obj.image('profilepicture')
        if content_image:

            if ('request' in self.context):
                image_url = content_image.srcset(self.context['request'])
            else:
                image_url = content_image.srcset()

            image_url = {
                'imageUrl': image_url
            }
            return image_url
        
        return None

    class Meta:
        model = User
        fields = ('id', 'uuid', 'username', 'first_name', 'last_name', 'email', 'profile_picture')
        read_only_fields = ['username']


class LocalcosmosPublicUserSerializer(LocalcosmosUserSerializer):

    dataset_count = serializers.SerializerMethodField()

    def get_dataset_count(self, obj):
        return obj.dataset_count()

    class Meta:
        model = User
        fields = ('uuid', 'username', 'first_name', 'last_name', 'profile_picture', 'date_joined',
                  'dataset_count')


class RegistrationSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField()

    # adding those 2 lines will make these fields required for some odd reason
    #first_name = serializers.CharField(required=False)
    #last_name = serializers.CharField(required=False)
    email = serializers.EmailField()
    email2 = serializers.EmailField()

    client_id = serializers.CharField()
    platform = serializers.CharField()

    def validate_email(self, value):
        email_exists = User.objects.filter(email__iexact=value).exists()
        if email_exists:
            raise serializers.ValidationError(_('This email address is already registered.'))

        return value

    def validate(self, data):
        if data['email'] != data['email2']:
            raise serializers.ValidationError({'email2': _('The email addresses did not match.')})

        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': _('The passwords did not match.')})
        return data


    def create(self, validated_data):
        extra_fields = {}

        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')

        if first_name:
            extra_fields['first_name'] = first_name

        if last_name:
            extra_fields['last_name'] = last_name
        
        user = User.objects.create_user(validated_data['username'], validated_data['email'],
                                        validated_data['password'], **extra_fields)

        return user
    

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'first_name', 'last_name', 'email', 'email2', 'client_id',
                  'platform')


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ServerContentImageSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)

    source_image = serializers.ImageField(write_only=True) # not required for delete
    # cannot combine binary image and json field
    crop_parameters = serializers.CharField(allow_null=True, write_only=True)

    image_url = serializers.JSONField(read_only=True, source='srcset')


    def save(self, validated_data, content_instance, image_type, user, content_image=None):

        image_file = validated_data['source_image']
        content_type = ContentType.objects.get_for_model(content_instance)

        file_md5 = hashlib.md5(image_file.read()).hexdigest()
        # this line is extremely required. do not delete it. otherwise the file_ will not be read correctly
        image_file.seek(0)

        image_store = ServerImageStore(
            source_image = image_file,
            uploaded_by = user,
            md5 = file_md5,
        )

        image_store.save()

        crop_parameters = validated_data.get('crop_parameters', None)
        
        if content_image:

            content_image.image_store = image_store

            # has to be valid json
            if crop_parameters:
                content_image.crop_parameters = json.dumps(crop_parameters)
            
            content_image.save()

            new_content_image = content_image
        
        else:
            
            new_content_image = ServerContentImage(
                image_store=image_store,
                content_type=content_type,
                object_id=content_instance.id,
                image_type=image_type,
            )

            # has to be valid json
            if crop_parameters:
                new_content_image.crop_parameters = json.dumps(crop_parameters)

            new_content_image.save()

        return new_content_image

    # always return a dict
    def validate_crop_parameters(self, value):

        parsed_value = {}

        if value:
            try:
                parsed_value = json.loads(value)
                required_numbers = ['x', 'y', 'width', 'height']
                for key in required_numbers:
                    if key not in parsed_value:
                        raise serializers.ValidationError('cropParameters require {0}'.format(key))
                    else:
                        try:
                            number = int(parsed_value[key])
                        except:
                            raise serializers.ValidationError('cropParameters have to be integers'.format(key))
                    
            except:
                raise serializers.ValidationError('Invalid cropParameters')

        return parsed_value
            


class ContactUserSerializer(serializers.Serializer):
    
    subject = serializers.CharField()
    message = serializers.CharField(min_length=10)
    

#################################################################################################
#
# Taxon Profile Serializers
#
#################################################################################################

class ImageUrlSerializer(serializers.Serializer):
    _1x = serializers.CharField(source='1x', read_only=True)
    _2x = serializers.CharField(source='2x', read_only=True)
    _4x = serializers.CharField(source='4x', read_only=True)
    
    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.app_url = None
        if self.app:
            self.app_url = app.get_url()

    def to_representation(self, instance):
        data = instance.copy()
        if self.app_url:
            for image_size, url in data.items():
                if url:
                    absolute_url = os.path.join(self.app_url, url.lstrip('/'))
                    if not absolute_url.startswith('https://') and not absolute_url.startswith('http://'):
                        absolute_url = 'https://' + absolute_url
                    data[image_size] = absolute_url
        else:
            # error
            raise ValueError("App url is not set. Cannot resolve image URLs.")
        return data

class LicenceSerializer(serializers.Serializer):
    licence = serializers.CharField(allow_null=True, required=False)
    licenceVersion = serializers.CharField(allow_null=True, required=False)
    creatorName = serializers.CharField(allow_null=True, required=False)
    creatorLink = serializers.CharField(allow_null=True, required=False)
    sourceLink = serializers.CharField(allow_null=True, required=False)

class ImageSerializer(serializers.Serializer):
    text = serializers.CharField(allow_null=True, required=False, read_only=True)
    altText = serializers.CharField(allow_null=True, required=False, read_only=True)
    title = serializers.CharField(allow_null=True, required=False, read_only=True)
    imageUrl = ImageUrlSerializer(read_only=True)
    licence = LicenceSerializer(read_only=True)

    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        
    def get_licence(self, instance):
        
        registry = self.app.get_licence_registry(app_state='published')
        
        if not registry:
            raise ValueError("Licence registry is not available in the app instance.")

        licences = registry['licences']
        licence = licences.get(instance['imageUrl']['1x'], None)
            
        if not licence:
            raise ValueError("Licence not found for the image URL: {}".format(instance['imageUrl']['1x']))
        
        return licence

    def to_representation(self, instance):
        data = instance.copy()  # Create a copy of the instance to avoid modifying it directly
        data['imageUrl'] = ImageUrlSerializer(instance['imageUrl'], app=self.app).data
        data['licence'] = self.get_licence(instance)
        return data

class TextSerializer(serializers.Serializer):
    taxonTextType = serializers.CharField(read_only=True)
    shortText = serializers.CharField(allow_null=True, required=False, read_only=True)
    shortTextKey = serializers.CharField(allow_null=True, required=False, read_only=True)
    longText = serializers.CharField(allow_null=True, required=False, read_only=True)
    longTextKey = serializers.CharField(allow_null=True, required=False, read_only=True)
    
class CategorizedTextSerializer(serializers.Serializer):
    category = serializers.CharField(read_only=True)
    texts = TextSerializer(many=True, read_only=True)
    
class ImagesSerializer(serializers.Serializer):
    primary = ImageSerializer(read_only=True)
    taxonProfileImages = serializers.ListField(child=ImageSerializer(read_only=True), required=False, read_only=True)
    nodeImages = serializers.ListField(child=ImageSerializer(read_only=True), required=False, read_only=True)
    taxonImages = serializers.ListField(child=ImageSerializer(read_only=True), required=False, read_only=True)

    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

    def to_representation(self, instance):
        data = {}
        if instance.get('primary'):
            data['primary'] = ImageSerializer(instance['primary'], app=self.app).data
        else:
            data['primary'] = None

        for field in ['taxonProfileImages', 'nodeImages', 'taxonImages']:
            images = instance.get(field, [])
            data[field] = [ImageSerializer(img, app=self.app).data for img in images]
        return data

class SynonymSerializer(serializers.Serializer):
    taxonLatname = serializers.CharField(read_only=True)
    taxonAuthor = serializers.CharField(read_only=True)
    
class SeoSerializer(serializers.Serializer):
    title = serializers.CharField(allow_null=True, required=False, read_only=True)
    meta_description = serializers.CharField(allow_null=True, required=False, read_only=True)
    
class ExternalMediaSerializer(serializers.Serializer):
    mediaType = serializers.ChoiceField(choices=EXTERNAL_MEDIA_TYPES, read_only=True)
    url = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    author = serializers.CharField(allow_null=True, required=False, read_only=True)
    licence = serializers.CharField(allow_null=True, required=False, read_only=True)
    caption = serializers.CharField(allow_null=True, required=False, read_only=True)
    altText = serializers.CharField(allow_null=True, required=False, read_only=True)
    

class TaxonRelationshipTaxonSerializer(serializers.Serializer):
    taxonSource = serializers.CharField(read_only=True)
    taxonLatname = serializers.CharField(read_only=True)
    taxonAuthor = serializers.CharField(read_only=True)
    nameUuid = serializers.CharField(read_only=True)
    taxonNuid = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    localizedSlug = serializers.DictField(child=serializers.CharField(read_only=True), read_only=True)
    gbifNubkey = serializers.IntegerField(read_only=True, allow_null=True)
    image = ImageSerializer(read_only=True)
    vernacular = serializers.DictField(child=serializers.CharField(read_only=True), read_only=True)
    hasTaxonProfile = serializers.BooleanField(read_only=True)
    shortProfile = serializers.CharField(allow_null=True, required=False, read_only=True)
    taxonProfileId = serializers.IntegerField(read_only=True, allow_null=True)
    
    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.language = kwargs.get('language', self.app.primary_language if self.app else None)
        
    def get_taxon_profile(self, instance):
        
        taxon_profile = None
        if instance['hasTaxonProfile'] == True and self.language:
            features = self.app.get_features('published')
            localized_taxon_profiles_path = features['TaxonProfiles']['localizedFiles'].get(self.language, {})
            if localized_taxon_profiles_path:
                root = self.app.get_installed_app_path('published')
                taxon_profile_path = os.path.join(root, localized_taxon_profiles_path.lstrip('/'), instance['taxonSource'], instance['nameUuid'] + '.json')
                
                if os.path.isfile(taxon_profile_path):
                    with open(taxon_profile_path, 'r', encoding='utf-8') as f:
                        taxon_profile = json.load(f)
                
        return taxon_profile

    def to_representation(self, instance):
        taxon = instance.copy()
        
        taxon_profile = self.get_taxon_profile(instance)
        
        if taxon_profile:
            taxon['taxonProfileId'] = taxon_profile['taxonProfileId']
            taxon['vernacular'] = taxon_profile['vernacular']
        else:
            taxon['taxonProfileId'] = None
            taxon['vernacular'] = {}
        
        return taxon


class TaxonRelationshipSerializer(serializers.Serializer):
    taxon = TaxonRelationshipTaxonSerializer(read_only=True)
    relatedTaxon = TaxonRelationshipTaxonSerializer(read_only=True)
    description = serializers.CharField(allow_null=True, required=False, read_only=True)
    
    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        
    def to_representation(self, instance):
        data = instance.copy()
        data['taxon'] = TaxonRelationshipTaxonSerializer(instance['taxon'], app=self.app).data
        data['relatedTaxon'] = TaxonRelationshipTaxonSerializer(instance['relatedTaxon'], app=self.app).data
        return data


class TaxonRelationshipTypeSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    taxonRole = serializers.CharField(read_only=True, required=False, allow_null=True)
    relatedTaxonRole = serializers.CharField(read_only=True, required=False, allow_null=True)


class TaxonRelationshipsSerializer(serializers.Serializer):
    relationshipType = TaxonRelationshipTypeSerializer(read_only=True)
    relationships = serializers.ListField(child=TaxonRelationshipSerializer(read_only=True), read_only=True)
    
class TaxonSerializer(serializers.Serializer):
    taxonLatname = serializers.CharField(read_only=True)
    taxonAuthor = serializers.CharField(read_only=True)
    taxonSource = serializers.CharField(read_only=True)
    nameUuid = serializers.CharField(read_only=True)
    taxonNuid = serializers.CharField(read_only=True)
    
    
class MorphotypeProfileSerializer(serializers.Serializer):
    
    taxonProfileId = serializers.IntegerField(read_only=True)
    parentTaxonProfileId = serializers.IntegerField(read_only=True)
    morphotype = serializers.CharField(read_only=True)
    taxon = TaxonSerializer(read_only=True)
    vernacular = serializers.DictField(child=serializers.CharField(read_only=True), read_only=True)
    image = ImageSerializer(read_only=True)
    vernacular = serializers.DictField(child=serializers.CharField(read_only=True), read_only=True)
    link = serializers.CharField(read_only=True)
    
    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        
    def to_representation(self, instance):
        data = instance.copy()
        # this is just a placeholder and work in progress
        data['link'] = 'https://www.beachexplorer.org/arten/tringa-nebularia-cranium/steckbrief'
        return data


class TaxonProfileSerializer(serializers.Serializer):
    taxonLatname = serializers.CharField(read_only=True)
    taxonAuthor = serializers.CharField(read_only=True)
    taxonSource = serializers.CharField(read_only=True)
    nameUuid = serializers.CharField(read_only=True)
    taxonNuid = serializers.CharField(read_only=True)
    gbifNubkey = serializers.IntegerField(read_only=True, allow_null=True)
    image = ImageSerializer(read_only=True)
    shortProfile = serializers.CharField(allow_null=True, required=False, read_only=True)
    taxonProfileId = serializers.IntegerField(read_only=True)
    vernacular = serializers.DictField(child=serializers.CharField(read_only=True), read_only=True)
    allVernacularNames = serializers.DictField(child=serializers.ListField(child=serializers.CharField(read_only=True), read_only=True), read_only=True)
    texts = TextSerializer(many=True, read_only=True)
    categorizedTexts = CategorizedTextSerializer(many=True, read_only=True)
    images = ImagesSerializer(read_only=True)
    synonyms = SynonymSerializer(many=True, read_only=True)
    tags = serializers.ListField(child=serializers.CharField(read_only=True), required=False, read_only=True)
    seo = SeoSerializer(read_only=True)
    externalMedia = serializers.ListField(child=ExternalMediaSerializer(read_only=True), required=False, read_only=True)
    taxonRelationships = serializers.ListField(child=TaxonRelationshipsSerializer(read_only=True), required=False, read_only=True)
    morphotypeProfiles = serializers.ListField(child=MorphotypeProfileSerializer(read_only=True), required=False, read_only=True)
    isFeatured = serializers.BooleanField(read_only=True)

    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

    def to_representation(self, instance):
        
        if not self.app:
            raise ValueError("App instance is required for TaxonProfileSerializer.")
        
        image = None
        if instance.get('image'):
            image = ImageSerializer(instance['image'], app=self.app).data
            
        images = None
        if instance.get('images'):
            images = ImagesSerializer(instance['images'], app=self.app).data
            
        taxon_relationships = instance.get('taxonRelationships', [])
        
        taxon_relationships_serialized = []
        for tr in taxon_relationships:
            
            tr_serialized = {
                'relationshipType': TaxonRelationshipTypeSerializer(tr['relationshipType']).data,
                'relationships': []
            }
            
            for relation in tr['relationships']:
                relation_serialized = TaxonRelationshipSerializer(
                    relation,
                    context=self.context,
                    app=self.app
                ).data
                tr_serialized['relationships'].append(relation_serialized)
                
            taxon_relationships_serialized.append(tr_serialized)
            
        morphotype_profiles = []
        for mp in instance.get('morphotypeProfiles', []):
            mp_serialized = MorphotypeProfileSerializer(mp, app=self.app).data
            morphotype_profiles.append(mp_serialized)
            
        data = {
            'taxonLatname': instance['taxonLatname'],
            'taxonAuthor': instance['taxonAuthor'],
            'taxonSource': instance['taxonSource'],
            'nameUuid': instance['nameUuid'],
            'taxonNuid': instance['taxonNuid'],
            'gbifNubkey': instance.get('gbifNubkey', None),
            'image': image,
            'shortProfile': instance['shortProfile'],
            'taxonProfileId': instance['taxonProfileId'],
            'vernacular': instance['vernacular'],
            'allVernacularNames': instance['allVernacularNames'],
            'texts': instance['texts'],
            'categorizedTexts': instance['categorizedTexts'],
            'images': images,
            'synonyms': instance['synonyms'],
            'tags': instance['tags'],
            'seo': instance['seo'],
            'externalMedia': instance['externalMedia'],
            'taxonRelationships': taxon_relationships_serialized,
            'morphotypeProfiles': morphotype_profiles,
            'isFeatured': instance['isFeatured'],
        }

        return data


class TaxonProfileMinimalSerializer(serializers.Serializer):
    
    taxonProfileId = serializers.IntegerField(read_only=True)
    taxonLatname = serializers.CharField(read_only=True)
    taxonAuthor = serializers.CharField(read_only=True)
    vernacular = serializers.DictField(child=serializers.CharField(read_only=True), read_only=True)
    
    def __init__(self, *args, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

    def to_representation(self, instance):
        
        if not self.app:
            raise ValueError("App instance is required for TaxonProfileSerializer.")
        
        data = {
            'taxonProfileId': instance['taxonProfileId'],
            'taxonLatname': instance['taxonLatname'],
            'taxonAuthor': instance['taxonAuthor'],
            'vernacular': instance['vernacular'],
        }

        return data