"""
    Parser for the Page Admin
    - receives a template
    - extracts all cms microcontent relevant tags into model objects for ModelForm
    
"""

from .CMSObjects import CMSTag

class TemplateParser(object):

    def __init__(self, template):
        self.template = template
        self.cms_tags = []

    def parse(self):

        cms_tags_str = []

        tag_open = False

        cms_tag_open = False

        obj_open = False
        obj_buffer = ""

        source = self.template.source

        for char in source:

            if tag_open:
                obj_buffer += char
                if obj_buffer == "{% cms_":
                    cms_tag_open = True

                if char == "}":

                    if cms_tag_open:
                        cms_tags_str.append(obj_buffer)
                        
                    cms_tag_open = False
                    tag_open = False
                    obj_open = False

                    obj_buffer = ""
                continue

            elif obj_open:
                obj_buffer += char
                if obj_buffer == "{%":
                    tag_open = True

                elif char == "}":
                    obj_open = False
                continue

            elif char == "{":
                obj_open = True
                obj_buffer = char
                continue

        for tag_str in cms_tags_str:

            tag_content = tag_str.lstrip("{%").rstrip("%}").strip().split(" ")

            tag = tag_content.pop(0)

            tag_content = [t.strip("'") for t in tag_content]

            microcontent_category = tag.split("_")[-1]

            microcontent_type = tag_content.pop(0)

            tag_kwargs = {}

            # iterate ofer tag args and create kwargs if necessary
            for arg in tag_content:
                if arg.startswith("min-") or arg.startswith("max-"):
                    parts = arg.split("-")
                    tag_kwargs[parts[0]] = tag_kwargs[parts[1]]
            
            tagobj = CMSTag(microcontent_category, microcontent_type, *tag_content, **tag_kwargs)

            self.cms_tags.append(tagobj)

        return self.cms_tags

            
