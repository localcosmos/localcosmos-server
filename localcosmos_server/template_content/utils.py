def get_component_image_type(component_key, component_uuid, content_key):
    image_key = '{0}:{1}:{2}'.format(component_key, component_uuid, content_key)
    return image_key

PUBLISHED_IMAGE_TYPE_PREFIX = 'published-'
def get_published_image_type(image_type):
    return '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, image_type)