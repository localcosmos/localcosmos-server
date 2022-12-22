from rest_framework import serializers

from localcosmos_server.template_content.models import LocalizedTemplateContent, PUBLISHED_IMAGE_TYPE_PREFIX

from content_licencing.models import ContentLicenceRegistry

class LocalizedTemplateContentSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()
    navigationLinkName = serializers.SerializerMethodField()
    templateName = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    templateUrl = serializers.SerializerMethodField()
    contents = serializers.SerializerMethodField()

    template_definition = None

    def get_from_definition(self, localized_template_content, key):
        template_definition = self.get_template_definition(localized_template_content)
        return template_definition[key]


    def get_template_definition(self, localized_template_content):
        preview = self.context.get('preview', True)
        if not self.template_definition:
            if preview == True:
                self.template_definition = localized_template_content.template_content.draft_template.definition
            else:
                self.template_definition = localized_template_content.template_content.template.definition
        return self.template_definition

    def get_title(self, localized_template_content):
        preview = self.context.get('preview', True)
        if preview == True:
            return localized_template_content.draft_title
        return localized_template_content.published_title

    def get_navigationLinkName(self, localized_template_content):
        preview = self.context.get('preview', True)
        if preview == True:
            return localized_template_content.draft_navigation_link_name

        return localized_template_content.published_navigation_link_name

    def get_templateName(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'templateName')

    def get_version(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'version')

    def get_templateUrl(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'templateUrl')

    def get_contents(self, localized_template_content):
        preview = self.context.get('preview', True)

        if preview == True:
            supplied_contents = localized_template_content.draft_contents
        else:
            supplied_contents = localized_template_content.published_contents


        template_definition = self.get_template_definition(localized_template_content)

        contents = template_definition['contents'].copy()

        primary_language = localized_template_content.template_content.app.primary_language
        primary_locale_template_content = localized_template_content.template_content.get_locale(primary_language)

        if supplied_contents:

            for content_key, content in supplied_contents.items():
                contents[content_key]['value'] = content
        
        # add images to contents, according to the template definition
        for content_key, content_definition in template_definition['contents'].items():

            image_type = content_key

            if preview == False:
                image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, content_key)

            if content_definition['type'] == 'image':

                content_image = primary_locale_template_content.image(image_type=image_type)
                if content_image:

                    serializer = ContentImageSerializer(content_image)
                    contents[content_key]['value'] = serializer.data

            elif content_definition['type'] == 'multi-image':
                content_images = primary_locale_template_content.images(image_type=image_type)
                contents[content_key]['value'] = []
                for content_image in content_images:

                    serializer = ContentImageSerializer(content_image)
                    contents[content_key]['value'].append(serializer.data)
            # add images to contents, according to the template definition

        return contents


    class Meta:
        model = LocalizedTemplateContent
        fields = ['title', 'navigationLinkName', 'templateName', 'version', 'templateUrl', 'contents']


class ContentLicenceSerializer(serializers.ModelSerializer):

    licenceVersion = serializers.CharField(source='licence_version')
    creatorName = serializers.CharField(source='creator_name')
    creatorLink = serializers.CharField(source='creator_link')
    sourceLink = serializers.CharField(source='source_link')

    class Meta:
        model = ContentLicenceRegistry
        fields = ('licence', 'licenceVersion', 'creatorName', 'creatorLink', 'sourceLink')


class ContentImageSerializer(serializers.Serializer):
    
    imageUrl = serializers.SerializerMethodField()
    licence = serializers.SerializerMethodField()

    def get_imageUrl(self, content_image):
        return content_image.image_url()

    def get_licence(self, content_image):

        image_store = content_image.image_store
        licence = image_store.licences.first()

        serializer = ContentLicenceSerializer(licence)

        return serializer.data