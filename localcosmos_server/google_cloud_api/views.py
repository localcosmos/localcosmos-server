###################################################################################################################
#
# LOCAL COSMOS GOOGLE CLOUD API
# - communication between app installations and the lc server
# - some endpoints are app-specific, some are not
# - app endpoint scheme: /<str:app_uuid>/{ENDPOINT}/
#
###################################################################################################################
import os, io
from google.cloud import vision
from google.cloud.vision import types

from rest_framework.views import APIView
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer

from rest_framework import status

from localcosmos_server.models import App

from .serializers import ImageSerializer




##################################################################################################################
#
#   APP SPECIFIC API ENDPOINTS
#
##################################################################################################################

'''
    Upload one and more images to google
'''

class ImageRecognition(APIView):

    serializer_class = ImageSerializer

    def post(self, request, *args, **kwargs):
        # Instantiates a client
        client = vision.ImageAnnotatorClient()

        # The name of the image file to annotate
        file_name = '/home/tom/albatros2.jpg'

        # Loads the image into memory
        with io.open(file_name, 'rb') as image_file:
            content = image_file.read()

        image = types.Image(content=content)

        # Performs label detection on the image file
        response = client.label_detection(image=image)
        labels = response.label_annotations

        print('Labels:')
        for label in labels:
            print(label.description)
        
