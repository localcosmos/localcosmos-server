TEMPLATE_CONTENT_TYPE_TEXT = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/observation-form.schema.json",
    "title": "Template content of type text",
    "description": "Part of a template content page",
    "type": "string",
    "additionalProperties": False,
}

TEMPLATE_CONTENT_TYPE_TEXT_MULTIPLE = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/observation-form.schema.json",
    "title": "Template content of type multiple text",
    "description": "Part of a template content page",
    "type": "array",
    "items": {
        "type": "string"
    },
    "additionalProperties": False,
}

TEMPLATE_CONTENT_TYPE_TEMPLATECONTENTLINK = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/observation-form.schema.json",
    "title": "Template content of type template content link",
    "description": "Part of a template content page. A link to another existing template content.",
    "type": "object",
    "properties": {
        "pk": {
            "type": "string",
        },
        "slug": {
            "type": "string",
        },
        "templateName": {
            "type": "string"
        },
        "title": {
            "type": "string"
        },
        "url": {
            "type": "string"
        }
    },
    "additionalProperties": False,
    "required": ["pk", "slug", "templateName", "title", "url"]
}

TEMPLATE_CONTENT_TYPE_COMPONENT = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/observation-form.schema.json",
    "title": "Template content of type component",
    "description": "Part of a template content page. A component consisting of content types",
    "type": "object",
    "properties": {
        "uuid": {
            "type": "string",
        },
    },
    "additionalProperties": True,
    "required": ["uuid"]
}