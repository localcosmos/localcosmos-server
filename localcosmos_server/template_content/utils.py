def get_component_image_key(component_key, component_uuid, content_key):

    image_key = '{0}:{1}:{2}'.format(component_key, component_uuid, content_key)
    return image_key