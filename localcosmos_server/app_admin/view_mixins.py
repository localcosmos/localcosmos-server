from django.core.exceptions import PermissionDenied

import rules

class ExpertOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        has_access = rules.test_rule('app.is_expert', request.user, request.app)

        if not has_access:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class AdminOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        has_access = rules.test_rule('app.is_admin', request.user, request.app)

        if not has_access:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)
        
