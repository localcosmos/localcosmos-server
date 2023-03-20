from rest_framework import serializers

from localcosmos_server.template_content.models import LocalizedTemplateContent, PUBLISHED_IMAGE_TYPE_PREFIX

from content_licencing.models import ContentLicenceRegistry

from localcosmos_server.template_content.utils import get_component_image_type, get_published_image_type

class LocalizedTemplateContentSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()
    templateName = serializers.SerializerMethodField()
    templatePath = serializers.SerializerMethodField()
    
    version = serializers.SerializerMethodField()
    
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

    def get_templateName(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'templateName')

    def get_version(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'version')

    def get_templatePath(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'templatePath')

    def get_image_data(self, content_definition, localized_template_content, image_type):

        preview = self.context.get('preview', True)

        if preview == False:
            image_type = get_published_image_type(image_type)

        if content_definition.get('allowMultiple', False) == True:
            content_images = localized_template_content.images(image_type=image_type)
            
            image_data = []
            for content_image in content_images:

                serializer = ContentImageSerializer(content_image)
                image_data.append(serializer.data)

            return image_data
        else:
            content_image = localized_template_content.image(image_type=image_type)

            if content_image:

                serializer = ContentImageSerializer(content_image)
                image_data = serializer.data
                return image_data

    
    def get_component_with_image_data(self, component_key, component, component_definition, component_uuid,
        localized_template_content, image_getter):

        for component_content_key, component_content_definition in component_definition['contents'].items():

            if component_content_definition['type'] == 'image':

                image_type = get_component_image_type(component_key, component_uuid, component_content_key)

                image_data = image_getter(component_content_definition, localized_template_content, image_type)

                component[component_content_key] = image_data
        
        return component


    def get_contents(self, localized_template_content):

        preview = self.context.get('preview', True)

        contents = {}

        if preview == True:
            if localized_template_content.draft_contents:
                contents = localized_template_content.draft_contents.copy()
        else:
            contents = localized_template_content.published_contents.copy()

        template_definition = self.get_template_definition(localized_template_content)

        primary_language = localized_template_content.template_content.app.primary_language
        primary_locale_template_content = localized_template_content.template_content.get_locale(primary_language)

        # add imageUrl to contents, according to the template definition
        for content_key, content_definition in template_definition['contents'].items():

            content = contents.get(content_key, None)

            if content_definition['type'] == 'image':

                image_type = content_key

                image_data = self.get_image_data(content_definition, primary_locale_template_content, image_type)
                contents[content_key] = image_data

            elif content_definition['type'] == 'component' and content != None:

                component_key = content_key

                if component_key in contents:
                    
                    if preview == True:
                        component_template = primary_locale_template_content.template_content.get_component_template(
                            component_key)
                    else:
                        component_template = primary_locale_template_content.template_content.get_published_component_template(
                            component_key)

                    component_definition = component_template.definition

                    # one or more components?
                    if content_definition.get('allowMultiple', False) == True:

                        components = contents[component_key]

                        for component_index, component in enumerate(components, 0):

                            component_uuid = component['uuid']

                            component_with_image_data = self.get_component_with_image_data(component_key, component,
                                component_definition, component_uuid, localized_template_content, self.get_image_data)

                            content[component_index] = component_with_image_data

                    else:
                        
                        component = contents[component_key]

                        component_uuid = component['uuid']

                        component_with_image_data = self.get_component_with_image_data(component_key, component,
                            component_definition, component_uuid, localized_template_content, self.get_image_data)

                        content[component_index] = component_with_image_data

        return contents

    class Meta:
        model = LocalizedTemplateContent
        fields = ['title', 'templateName', 'templatePath', 'version', 'contents']


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