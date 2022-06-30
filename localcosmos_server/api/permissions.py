from rest_framework import permissions

from localcosmos_server.models import App


##################################################################################################################
#
#   DataSet Creation
#   
#   - allow_anonymous_observations is set on an per-app-basis
#   - server-side check should be implemented in case the user changes this permission, otherwise old app installs could still upload
#   - this check uses the currently live webapp settings.json to check
#
##################################################################################################################

class CanCreateDataset(permissions.BasePermission):
    
    def has_permission(self, request, view):
        
        app_uuid = request.data['app_uuid']
        app = App.objects.get(uuid=app_uuid)

        app_state = 'published'

        if 'review' in request.data:
            app_state = 'review'
        
        app_settings = app.get_settings(app_state=app_state)
        
        allow_anonymous_observations = app_settings.get('allow_anonymous_observations', False)

        if allow_anonymous_observations == False and request.user.is_authenticated == False:
            return False

        return True
        


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

        # determine if the user is allowed to alter or delete a dataset
        # owner can be determined by device uuid or dataset.user == request.user
        if request.user == dataset.user:
            return True
        
        elif 'client_id' in request.query_params and request.query_params['client_id'] == dataset.client_id:
            return True
        
        return False


