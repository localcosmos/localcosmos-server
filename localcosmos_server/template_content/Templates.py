from django.conf import settings
import os, json

TEMPLATE_CONTENT_FOLDER_NAME = 'template_content'
UPLOADED_TEMPLATES_ROOT = os.path.join(settings.MEDIA_ROOT, TEMPLATE_CONTENT_FOLDER_NAME)

'''
definition :

    {
      "templateName" : "Neobiota", # a verbose name, constant
      "version" : 1, # integer version
      "templateUrl": "/fact-sheet/neobiota/{slug}", # the url supplied by the frontend for the preview
      "contents": {
        "headline": {
          "type": "text",
          "widget" : "TextInput"
        },
        "titleImage": {
          "type": "image"
        },
        "description": {
          "type": "text",
          "format": "layoutable-full"
        },
        "images": {
          "type": "multi-image"
        }
      }
    }
'''


class TemplatePaths:

    @property
    def frontend_templates_path(self):
        app_root = self.app.get_installed_app_path(app_state='preview')
        return os.path.join(app_root, TEMPLATE_CONTENT_FOLDER_NAME, self.template_type)

    @property
    def uploaded_templates_path(self):
        return os.path.join(UPLOADED_TEMPLATES_ROOT, self.app.uid, self.template_type)



'''
    A template consists of 2 files:
    - a .json file as a definition
    - a template file containing the template as a string
    - draft should use the newest file 
      (-> check version if the template exists in both the frontend and the uploaded folder)
'''
class Template(TemplatePaths):

    # name is used to identify the folder of the template files
    def __init__(self, app, name, template_type, template_definition_filepath=None):

        self.app = app
        self.name = name
        self.template_type = template_type

        self.template_definition_filepath = None
        
        self.template_exists = True

        if template_definition_filepath:
            self.template_definition_filepath = template_definition_filepath

            self.definition = self.read_template_definition_file(self.template_definition_filepath)
        
        else:
            try:
                self.load_template_definition_from_file()
            except FileNotFoundError:
                self.template_exists = False

                
    @property
    def frontend_template_folder(self):
        return os.path.join(self.frontend_templates_path, self.name)

    @property
    def uploaded_template_folder(self):
        return os.path.join(self.uploaded_templates_path, self.name)


    def get_template_definition_filepath(self, template_folder):

        template_definition_filepath = None

        if os.path.isdir(template_folder):
            
            for filename in os.listdir(template_folder):
                
                filepath = os.path.join(template_folder, filename)

                if os.path.isfile(filepath):

                    basename, ext = os.path.splitext(filepath)

                    # only one json file is allowed
                    if ext == '.json':
                        template_definition_filepath = filepath
                        break

        return template_definition_filepath

    def read_template_definition_file(self, template_definition_filepath):

        definition = None

        if template_definition_filepath:

            with open(template_definition_filepath, 'r') as template_definition_file:
                definition = json.loads(template_definition_file.read())

        
        return definition

    '''
        - first, look up the frontend template_content folder for the template
        - second, check uploaded templates, compare version with frontend's template
    '''  
    def load_template_definition_from_file(self):

        definition = None
        template_definition_filepath = None

        frontend_template_definition_filepath = self.get_template_definition_filepath(
            self.frontend_template_folder)

        frontend_template_definition = self.read_template_definition_file(frontend_template_definition_filepath)

        
        if frontend_template_definition:
            definition = frontend_template_definition
            template_definition_filepath = frontend_template_definition_filepath

        uploaded_template_definition_filepath = self.get_template_definition_filepath(
            self.uploaded_template_folder)

        uploaded_template_definition = self.read_template_definition_file(uploaded_template_definition_filepath)

        if uploaded_template_definition:
            
            if uploaded_template_definition['version'] > frontend_template_definition['version']:
                definition = uploaded_template_definition
                template_definition_filepath = uploaded_template_definition_filepath

        if not definition:
            msg = 'Template "{0}" not found. Looked in: {1} , {2}'.format(self.name, self.frontend_templates_path,
                self.uploaded_templates_path)
            raise FileNotFoundError(msg)

        self.definition = definition

        self.template_definition_filepath = template_definition_filepath


'''
    there are several app builds:
    - preview
    - review
    - published

    preview and review have the same frontend version
'''
class Templates(TemplatePaths):

    def __init__(self, app, template_type):
        self.app = app
        self.template_type = template_type


    def get_all_templates(self):

        templates = {}

        # iterate over all directories of frontend_templates_folder
        if os.path.isdir(self.frontend_templates_path):

            for frontend_dirname in os.listdir(self.frontend_templates_path):
                template = Template(self.app, frontend_dirname, self.template_type)
                templates[frontend_dirname] = template

        if os.path.isdir(self.uploaded_templates_path):

            for dirname in os.listdir(self.uploaded_templates_path):
                template = Template(self.app, dirname, self.template_type)

                if dirname in templates:
                    if template.definition['version'] < templates[dirname].definition['version']:
                        continue
                        
                templates[dirname] = template

        return templates