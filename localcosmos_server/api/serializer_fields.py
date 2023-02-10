from rest_framework import serializers

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