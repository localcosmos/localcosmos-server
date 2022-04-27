from django.forms import ImageField
from django.core.exceptions import ValidationError
from django.core.validators import get_available_image_extensions, FileExtensionValidator

from localcosmos_server.validators import validate_svg

allowed_extensions = get_available_image_extensions() + ['svg']

validate_svg_and_image_file_extension = FileExtensionValidator(
    allowed_extensions=allowed_extensions,
)

class SVGandImageField(ImageField):

    default_validators = [validate_svg_and_image_file_extension]

    def to_python(self, data):

        try:
            f = super().to_python(data)
        except ValidationError:
            root = validate_svg(data)

        return data
    
