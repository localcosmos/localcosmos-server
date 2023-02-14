from rest_framework import permissions

from localcosmos_server.models import App

class AppMustExist(permissions.BasePermission):

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