from rest_framework.schemas.openapi import AutoSchema
from .serializers import (
    RegisterFCMDeviceSerializer,
)

class RegisterFCMDeviceSchema(AutoSchema):
    def get_operation_id(self, path, method):
        return 'registerFCMDevice'

    def get_request_serializer(self, path, method):
        return RegisterFCMDeviceSerializer()

    def get_responses(self, path, method):
        return {
            '200': {
                'description': 'FCM registration token updated for this device.',
            },
            '201': {
                'description': 'FCM device registered for this device.',
            },
            '400': {
                'description': 'Invalid request body.',
            },
            '401': {
                'description': 'Authentication credentials were not provided.',
            },
        }


class DeregisterFCMDeviceSchema(AutoSchema):
    def get_operation_id(self, path, method):
        return 'deregisterFCMDevice'

    def get_request_serializer(self, path, method):
        return None

    def get_responses(self, path, method):
        return {
            '204': {
                'description': 'FCM device deregistered successfully.',
            },
            '401': {
                'description': 'Authentication credentials were not provided.',
            },
            '404': {
                'description': 'No FCM device registration found for this device.',
            },
        }

