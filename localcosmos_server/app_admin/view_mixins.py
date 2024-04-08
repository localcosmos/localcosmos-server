from django.core.exceptions import PermissionDenied

class ExpertOnlyMixin:
    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return False

        has_access = request.user.has_perm('app.is_expert', request.app)

        if not has_access:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class AdminOnlyMixin:
    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return False

        has_access = request.user.has_perm('app.is_admin', request.app)

        if not has_access:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)
        
