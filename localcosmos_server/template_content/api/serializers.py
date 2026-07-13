from rest_framework import serializers

from localcosmos_server.template_content.models import (LocalizedTemplateContent, LocalizedNavigation,
    PUBLISHED_IMAGE_TYPE_PREFIX)

from content_licencing.models import ContentLicenceRegistry

from localcosmos_server.template_content.utils import get_component_image_type, get_published_image_type

# do not replace camelCase with underscore_case without adapting app_kit's ContentImageBuilder.build_licence
class LocalizedTemplateContentSerializer(serializers.ModelSerializer):
    
    uuid = serializers.SerializerMethodField()
    
    language = serializers.SerializerMethodField()

    title = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    
    slug = serializers.SerializerMethodField()
    
    createdAt = serializers.SerializerMethodField()
    lastModified = serializers.SerializerMethodField()
    publishedAt = serializers.SerializerMethodField()
    
    templateName = serializers.SerializerMethodField()
    
    version = serializers.SerializerMethodField()
    
    contents = serializers.SerializerMethodField()

    linkedTaxa = serializers.SerializerMethodField()
    linkedTaxonProfiles = serializers.SerializerMethodField()

    template_definition = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.linked_ltc_cache = {}

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
    
    def get_uuid(self, localized_template_content):
        return str(localized_template_content.template_content.uuid)
    
    def get_language(self, localized_template_content):
        return localized_template_content.language

    def get_title(self, localized_template_content):
        preview = self.context.get('preview', True)
        if preview == True:
            return localized_template_content.draft_title
        return localized_template_content.published_title
    
    def get_slug(self, localized_template_content):
        return localized_template_content.slug
    
    def get_author(self, localized_template_content):
        preview = self.context.get('preview', True)
        if preview == True:
            return localized_template_content.author
        return localized_template_content.published_author
    
    def get_createdAt(self, localized_template_content):
        return localized_template_content.created_at.isoformat()
    
    def get_lastModified(self, localized_template_content):
        if localized_template_content.last_modified:
            return localized_template_content.last_modified.isoformat()
        return None
    
    def get_publishedAt(self, localized_template_content):
        if localized_template_content.published_at:
            return localized_template_content.published_at.isoformat()
        return None
    
    def get_templateName(self, localized_template_content):
        return self.get_from_definition(localized_template_content, 'templateName')

    # this is not the version defined in the template definition, but the published version of the template content. it is present in the built version, but not in the app kit's jsonbuilder yet. it might be a good addition to the app kit as well.
    def get_version(self, localized_template_content):
        if localized_template_content.published_version:
            return localized_template_content.published_version
        return localized_template_content.draft_version
    
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

            return None
    
    def hydrate_component_contents(self, component_key, component, component_definition,
        localized_template_content):

        if component:
        
            component_uuid = component['uuid']

            for component_content_key, component_content_definition in component_definition['contents'].items():

                if component_content_definition['type'] == 'image':

                    image_type = get_component_image_type(component_key, component_uuid, component_content_key)

                    image_data = self.get_image_data(component_content_definition, localized_template_content, image_type)

                    component[component_content_key] = image_data

                elif component_content_definition['type'] == 'templateContentLink':

                    preview = self.context.get('preview', True)
                    linked_content = component.get(component_content_key, None)

                    if type(linked_content) is list:
                        hydrated_links = []
                        for link_item in linked_content:
                            hydrated_links.append(self.hydrate_template_content_link(
                                link_item, localized_template_content, preview))
                        component[component_content_key] = hydrated_links

                    elif linked_content is not None:
                        component[component_content_key] = self.hydrate_template_content_link(
                            linked_content, localized_template_content, preview)
            
        return component

    def get_linked_localized_template_content(self, linked_content, localized_template_content):
        linked_ltc = None

        linked_pk = linked_content.get('pk', None)
        cache_key = str(linked_pk)

        if cache_key in self.linked_ltc_cache:
            return self.linked_ltc_cache[cache_key]

        if linked_pk:
            linked_ltc = LocalizedTemplateContent.objects.filter(pk=linked_pk).first()

        # Fallback for older payloads without pk
        if not linked_ltc:
            linked_slug = linked_content.get('slug', None)
            linked_template_name = linked_content.get('templateName', None)
            if linked_slug and linked_template_name:
                linked_ltc = LocalizedTemplateContent.objects.filter(
                    template_content__app=localized_template_content.template_content.app,
                    language=localized_template_content.language,
                    slug=linked_slug,
                    template_content__draft_template_name=linked_template_name,
                ).first()

        self.linked_ltc_cache[cache_key] = linked_ltc
        return linked_ltc

    def hydrate_template_content_link(self, linked_content, localized_template_content, preview):
        if type(linked_content) is not dict:
            return linked_content

        linked_ltc = self.get_linked_localized_template_content(linked_content, localized_template_content)
        if not linked_ltc:
            return linked_content

        linked_data = linked_content.copy()

        if preview == True:
            linked_data['title'] = linked_ltc.draft_title
            linked_data['author'] = linked_ltc.author
        else:
            linked_data['title'] = linked_ltc.published_title or linked_ltc.draft_title
            linked_data['author'] = linked_ltc.published_author or linked_ltc.author

        template_name = linked_ltc.template_content.draft_template_name
        linked_data['pk'] = str(linked_ltc.pk)
        linked_data['slug'] = linked_ltc.slug
        linked_data['templateName'] = template_name

        app_settings = localized_template_content.template_content.app.get_settings()
        if 'templateContent' in app_settings and 'urlPattern' in app_settings['templateContent']:
            linked_data['url'] = app_settings['templateContent']['urlPattern'].replace(
                '{slug}', linked_ltc.slug).replace('{templateName}', template_name)

        return linked_data


    def get_contents(self, localized_template_content):

        preview = self.context.get('preview', True)

        contents = {}

        if preview == True:
            if localized_template_content.draft_contents:
                contents = localized_template_content.draft_contents.copy()
        else:
            if localized_template_content.published_contents:
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
                
                # content variable can be a list or component dict
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

                            component_with_image_data = self.hydrate_component_contents(component_key, component,
                                component_definition, localized_template_content)

                            content[component_index] = component_with_image_data
                        
                        contents[component_key] = content

                    else:
                        
                        component = contents[component_key]

                        component_with_image_data = self.hydrate_component_contents(component_key, component,
                            component_definition, localized_template_content)

                        contents[component_key] = component_with_image_data
            
            
            elif content_definition['type'] == 'stream' and content != None:
                
                stream_key = content_key

                if stream_key in contents:

                    stream_items = contents[stream_key]

                    for stream_item_index, stream_item in enumerate(stream_items, 0):
                        
                        component_template_name = stream_item['templateName']
                        
                        if preview == True:
                            component_template = primary_locale_template_content.template_content.get_component_template(
                                stream_key, component_template_name)
                        else:
                            component_template = primary_locale_template_content.template_content.get_published_component_template(
                                stream_key, component_template_name)
                            
                            
                        component_definition = component_template.definition

                        stream_item_with_image_data = self.hydrate_component_contents(stream_key, stream_item,
                            component_definition, localized_template_content)

                        stream_items[stream_item_index] = stream_item_with_image_data
                    
                    contents[stream_key] = stream_items

            elif content_definition['type'] == 'templateContentLink' and content != None:
                if type(content) is list:
                    link_items = []
                    for link_item in content:
                        hydrated_link = self.hydrate_template_content_link(link_item,
                            localized_template_content, preview)
                        link_items.append(hydrated_link)
                    contents[content_key] = link_items
                else:
                    hydrated_link = self.hydrate_template_content_link(content,
                        localized_template_content, preview)
                    contents[content_key] = hydrated_link

        return contents

    # hasTaxonProfile might be a good addition for the api. it is also present in the built version
    def get_linkedTaxa(self, localized_template_content):

        linked_taxa = []
        restrictions = localized_template_content.template_content.taxonomic_restrictions

        for restriction in restrictions.all():
            
            taxon = restriction.taxon
            taxon_data = {
                'taxonSource': taxon.taxon_source,
                'taxonLatname': taxon.taxon_latname,
                'taxonAuthor': taxon.taxon_author,
                'nameUuid': taxon.name_uuid,
                'taxonNuid': taxon.taxon_nuid,
            }
            linked_taxa.append(taxon_data)

        return linked_taxa
    
    # not implemented yet for the api. App Kits jsonbuilder has it already.
    def get_linkedTaxonProfiles(self, localized_template_content):
        return []


    class Meta:
        model = LocalizedTemplateContent
        fields = ['title', 'templateName', 'version', 'contents', 'linkedTaxa', 'linkedTaxonProfiles',
                  'publishedAt', 'createdAt', 'lastModified', 'uuid', 'language', 'slug', 'author']


# do not replace camelCase with underscore_case without adapting app_kit's ContentImageBuilder.build_licence
class ContentLicenceSerializer(serializers.ModelSerializer):

    licenceVersion = serializers.CharField(source='licence_version')
    creatorName = serializers.CharField(source='creator_name')
    creatorLink = serializers.CharField(source='creator_link')
    sourceLink = serializers.CharField(source='source_link')

    class Meta:
        model = ContentLicenceRegistry
        fields = ('licence', 'licenceVersion', 'creatorName', 'creatorLink', 'sourceLink')

# do not replace imageUrl with image_url without adapting app_kit's ContentImageBuilder.build_licence
class ContentImageSerializer(serializers.Serializer):
    
    imageUrl = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    altText = serializers.SerializerMethodField()
    licence = serializers.SerializerMethodField()

    def get_imageUrl(self, content_image):
        return content_image.image_urls()

    def get_licence(self, content_image):

        image_store = content_image.image_store
        licence = image_store.licences.first()

        serializer = ContentLicenceSerializer(licence)

        return serializer.data
    
    def get_title(self, content_image):
        return content_image.title
    
    def get_text(self, content_image):
        return content_image.text
    
    def get_altText(self, content_image):
        return content_image.alt_text
    
    
class LocalizedNavigationSerializer(serializers.ModelSerializer):
    
    navigation = serializers.SerializerMethodField()
    
    def get_navigation(self, localized_navigation):
        preview = self.context.get('preview', True)
        
        if preview == True:
            return localized_navigation.serialize()

        return localized_navigation.published_navigation
    
    class Meta:
        model = LocalizedNavigation
        fields = ('navigation',)
        