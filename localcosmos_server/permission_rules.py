'''
    permission management via rules (django-rules) predicates
'''
import rules

from localcosmos_server.models import AppUserRole

@rules.predicate
def is_app_admin(user, app):
    if user.is_superuser or user.is_staff:
        return True
    return AppUserRole.objects.filter(app=app, user=user, role='admin').exists()


@rules.predicate
def is_expert(user, app):
    if user.is_superuser or user.is_staff:
        return True
    return AppUserRole.objects.filter(app=app, user=user, role__in=['admin', 'expert']).exists()


###################################################################################################################
#
#   STAFF ONLY
#
###################################################################################################################

# install an app
rules.add_perm('server.can_install_app', rules.is_staff)

###################################################################################################################
#
#   APP ADMINS ONLY
#
###################################################################################################################

# update an app
rules.add_perm('app.is_admin', is_app_admin)

###################################################################################################################
#
#   EXPERTS ONLY
#   - app admins are also experts
#
###################################################################################################################
rules.add_perm('app.is_expert', is_expert)

# accessing app admin
rules.add_perm('app_admin.has_access', is_expert)

# perm for review dataset
rules.add_perm('datasets.can_review_dataset', is_expert)

# perm for delete dataset
rules.add_perm('datasets.can_delete_dataset', is_expert)

# perm for update dataset
rules.add_perm('datasets.can_update_dataset', is_expert)
