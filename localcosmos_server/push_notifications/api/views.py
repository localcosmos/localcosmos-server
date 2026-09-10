from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from localcosmos_server.models import App
from django.db import transaction

from .schemas import RegisterFCMDeviceSchema, DeregisterFCMDeviceSchema

from .serializers import RegisterFCMDeviceSerializer, DeregisterFCMDeviceSerializer

from localcosmos_server.push_notifications.models import PushReceivingDevice
from localcosmos_server.api.permissions import AppMustExist

from fcm_django.models import FCMDevice

class RegisterFCMDeviceView(APIView):
    permission_classes = [AppMustExist]
    schema = RegisterFCMDeviceSchema()
    serializer_class = RegisterFCMDeviceSerializer

    def post(self, request, *args, **kwargs):
        
        app_uuid = kwargs['app_uuid']
        app = App.objects.get(uuid=app_uuid)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration_id = serializer.validated_data['registration_id']
        device_type = serializer.validated_data['type']
        client_id = serializer.validated_data['client_id']
        language_code = serializer.validated_data['language_code']

        with transaction.atomic():
            fcm_device, created = FCMDevice.objects.update_or_create(
                registration_id=registration_id,
                defaults={'type': device_type, 'active': True},
            )
            # delete any other device that was holding this token
            PushReceivingDevice.objects.filter(fcm_device=fcm_device).exclude(
                app=app, client_id=client_id
            ).delete()

            PushReceivingDevice.objects.update_or_create(
                app=app,
                client_id=client_id,
                defaults={'fcm_device': fcm_device, 'language_code': language_code},
            )

        return Response(status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DeregisterFCMDeviceView(APIView):
    permission_classes = [AppMustExist]
    schema = DeregisterFCMDeviceSchema()
    serializer_class = DeregisterFCMDeviceSerializer

    def delete(self, request, *args, **kwargs):
        
        app_uuid = kwargs['app_uuid']
        app = App.objects.get(uuid=app_uuid)
        
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_id = serializer.validated_data['client_id']
        receiving_device = PushReceivingDevice.objects.filter(app=app, client_id=client_id).first()
        if receiving_device is None:
            return Response({'detail': 'Device not found.'}, status=status.HTTP_404_NOT_FOUND)

        # CASCADE on fcm_device deletes receiving_device too
        receiving_device.fcm_device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)