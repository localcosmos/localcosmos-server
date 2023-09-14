from rest_framework import permissions

from localcosmos_server.models import App


##################################################################################################################
#
#   DataSet/ObservationForm Creation
#   
#   - allow_anonymous_observations is set on a per-app-basis
#   - server-side check should be implemented in case the app creator changes this permission,
#     otherwise old app installs could still upload
#   - this check uses the currently live webapp settings.json to check
#
##################################################################################################################

class AnonymousObservationsPermission(permissions.BasePermission):
    
    def has_permission(self, request, view):
        
        app_uuid = view.kwargs['app_uuid']
        app = App.objects.get(uuid=app_uuid)

        app_state = 'published'

        if 'review' in request.data:
            app_state = 'review'

        app_settings = app.get_settings(app_state=app_state)

        allow_anonymous_observations = app_settings['OPTIONS'].get('allowAnonymousObservations', False)
        
        if allow_anonymous_observations == False and request.user.is_authenticated == False:
            return False

        return True

class AnonymousObservationsPermissionOrGet(AnonymousObservationsPermission):

    def has_permission(self, request, view):

        if request.method == 'GET':
            return True
            
        return super().has_permission(request, view)

        


###################################################################################################################
#
#   DataSet Management
#
#   - only the Dataset owner may update/delete a dataset
#
###################################################################################################################

class DatasetOwnerOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, dataset):

        # allow read for all
        if request.method in permissions.SAFE_METHODS:
            return True

        try:
            client_id = request.data.get('client_id', None)
        except:
            client_id = None

        # determine if the user is allowed to alter or delete a dataset
        # owner can be determined by device uuid or dataset.user == request.user
        if request.user.is_authenticated == True and request.user == dataset.user:
            return True
        
        if not dataset.user and request.user.is_authenticated == False and client_id == dataset.client_id:
            return True
        
        return False


class DatasetAppOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, dataset):

        # allow read for all
        if request.method in permissions.SAFE_METHODS:
            return True

        if dataset.app_uuid == view.kwargs['app_uuid']:
            return True
        
        return False


class AuthenticatedOwnerOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, instance):

        if request.user == instance.user:
            return True
        return False



class MaxThreeInstancesPerUser(permissions.BasePermission):

    def has_permission(self, request, view):

        if request.method == 'POST':
            
            count = view.queryset.filter(user=request.user).count()
            if count >= 3:
                return False
            
        return super().has_permission(request, view)