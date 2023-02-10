from rest_framework import permissions

class OwnerOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        if obj == request.user:
            return True

        if getattr(obj, 'user', None) == request.user:
            return True

        return False