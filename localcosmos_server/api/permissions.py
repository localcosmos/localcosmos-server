from rest_framework import permissions

from localcosmos_server.models import App

class AppMustExist(permissions.BasePermission):

    # the message currently is not being shown
    message = 'App does not exist.'

    def has_permission(self, request, view):

        app_uuid = view.kwargs['app_uuid']

        app_exists = App.objects.filter(uuid=app_uuid).exists()

        if not app_exists:
            return False

        return True


class OwnerOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        if obj == request.user:
            return True

        if getattr(obj, 'user', None) == request.user:
            return True

        return False



class ServerContentImageOwnerOrReadOnly(permissions.BasePermission):

    allowed_image_types = {
        'LocalcosmosUser' : ['profilepicture']
    }

    def has_object_permission(self, request, view, obj):

        model_name = obj.__class__.__name__

        if model_name not in self.allowed_image_types or view.image_type not in self.allowed_image_types[model_name]:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if model_name == 'LocalcosmosUser' and obj == request.user:
            return True

        return False