from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from xml.etree import ElementTree

'''
    FileField Validators
'''

from django.core.validators import FileExtensionValidator
from io import BytesIO
from PIL import Image


def validate_svg(data):
    message = _('Invalid SVG file: could not detect SVG in XML tree of the file.')

    # We need to get a file object for Pillow. We might have a path or we might
    # have to read the data into memory.
    if hasattr(data, 'temporary_file_path'):
        file = data.temporary_file_path()
    else:
        if hasattr(data, 'file') and type(data.file) == BytesIO:
            file = data.file
            # make sure reading starts at line 1
            file.seek(0)
        else:
            if hasattr(data, 'read'):
                file = BytesIO(data.read())
            else:
                file = BytesIO(data['content'])
    
    try:
        doc = ElementTree.parse(file)
        root = doc.getroot()

        if 'svg' not in root.tag.lower():
            raise ValidationError(message)

        return root
    
    except:
        raise ValidationError(message)
        

class ImageRatioValidator:

    tolerance = 0.1

    # allowed_ratio_str is a 'width:height' string like '1:2' 
    def __init__(self, allowed_ratio_str=None):
        self.allowed_ratio_str = allowed_ratio_str
        if allowed_ratio_str:
            ratio_list = allowed_ratio_str.split(':')
            self.allowed_ratio = float(ratio_list[0])/float(ratio_list[1])
            self.error_message = _('Wrong image ratio. Upload a file with the dimensions w:h = %(ratio)s' % {
                'ratio' : self.allowed_ratio_str })
        else:
            self.allowed_ratio = None
            

    def __call__(self, image_file):

        if self.allowed_ratio != None:

            ext = image_file.name.split('.')[-1]
            filename = image_file.name.rstrip('.{ext}'.format(ext=ext))

            ext = ext.lower()

            validation_method_name = 'validate_%s' % ext
            
            if not hasattr(self, validation_method_name):
                raise ValidationError('Unsupported file extension: %s' % ext)

            validation_method = getattr(self, validation_method_name)
            validation_method(image_file)

    def validate_svg(self, image_file):
        root = validate_svg(image_file)

        # fix width and height, use viewBox
        svg_width = root.attrib.get('width', None)
        svg_height = root.attrib.get('height', None)
        
        root.attrib['width'] = '100%'
        root.attrib['height'] = '100%'

        view_box = root.attrib.get('viewBox', None)

        if not view_box:

            if svg_width and svg_height:
                view_box = '0 0 %s %s' % (svg_width, svg_height)
                
            else:
                message = _('Invalid SVG file: did neither find viewBox setting or width and height setting in the SVG file.')
                raise ValidationError(message)

        
        min_x, min_y, max_x, max_y = view_box.split(' ')

        svg_x = float(max_x) - float(min_x)
        svg_y = float(max_y) - float(min_y)

        svg_ratio = svg_x/svg_y

        if svg_ratio != self.allowed_ratio:
            raise ValidationError(self.error_message)
        

    def validate_png(self, image_file):
        self.validate_jpg(image_file)

    def validate_jpg(self, image_file):
        
        image_data = BytesIO(image_file.read())
        image = Image.open(image_data)
        w, h = image.size

        image_ratio = w/h

        # apply a tolerance
        # if using the cropping tool of photoshop or gimp, the ratio might be slightly off
        min_ratio = self.allowed_ratio - self.tolerance
        max_ratio = self.allowed_ratio + self.tolerance

        if image_ratio < min_ratio or image_ratio > max_ratio:
            raise ValidationError(self.error_message)

    def validate_jpeg(self, image_file):
        self.validate_jpg(image_file)
            
        
        

class ImageDimensionsValidator:

    # receives dimensions as a "WIDTHxHEIGHT" string like "1920x1080"
    def __init__(self, allowed_dimensions_str=None):
        self.allowed_dimensions_str = allowed_dimensions_str
        self.allowed_width = None
        self.allowed_height = None

        if allowed_dimensions_str:
            dimensions_list = allowed_dimensions_str.split('x')
            self.allowed_width = float(dimensions_list[0])
            self.allowed_height = float(dimensions_list[1])

            self.error_message = _('Wrong image dimensions. You image has to be EXACTLY width x height = %(dimensions)s' % {
                'dimensions' : self.allowed_dimensions_str, })

    def __call__(self, image_file):

        if self.allowed_width != None:

            ext = image_file.name.split('.')[-1]
            filename = image_file.name.rstrip('.{ext}'.format(ext=ext))

            ext = ext.lower()

            validation_method_name = 'validate_%s' % ext
            
            if not hasattr(self, validation_method_name):
                raise ValidationError('unsupported file extension: %s' % ext)

            validation_method = getattr(self, validation_method_name)
            validation_method(image_file)


    def validate_svg(self, image_file):
        root = validate_svg(image_file)
            

        # fix width and height, use viewBox
        svg_width = root.attrib.get('width', None)
        svg_height = root.attrib.get('height', None)
        
        root.attrib['width'] = '100%'
        root.attrib['height'] = '100%'

        view_box = root.attrib.get('viewBox', None)

        if not view_box:

            if svg_width and svg_height:
                view_box = '0 0 %s %s' % (svg_width, svg_height)
                
            else:
                message = _('Invalid SVG file: did neither find viewBox setting or width and height setting in the SVG file.')
                raise ValidationError(message)

        
        min_x, min_y, max_x, max_y = view_box.split(' ')

        svg_width = float(max_x) - float(min_x)
        svg_height = float(max_y) - float(min_y)

        if svg_width != self.allowed_width or svg_height != self.allowed_height:
            raise ValidationError(self.error_message)
        

    def validate_png(self, image_file):
        self.validate_jpg(image_file)

    def validate_jpg(self, image_file):
        
        image_data = BytesIO(image_file.read())
        image = Image.open(image_data)
        width, height = image.size

        if width != self.allowed_width or height != self.allowed_height:
            raise ValidationError(self.error_message)

    def validate_jpeg(self, image_file):
        self.validate_jpg(image_file)

    
