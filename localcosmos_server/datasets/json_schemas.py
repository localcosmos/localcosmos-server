OBSERVATION_FORM_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/observation-form.schema.json",
    "title": "Observation form",
    "description": "A Local Cosmos Observation Form",
    "type": "object",
    "properties": {
        "uuid": {
            "description": "The unique identifier for an observation form",
            "type": "string",
            "format": "uuid"
        },
        "version": {
            "description": "The version of the observation form",
            "type": "integer"
        },
        "name": {
            "description": "The name of the observation form",
            "type": "string"
        },
        "slug": {
            "description": "The slug of the observation form",
            "type": "string"
        },
        "options": {
            "type": "object"
        },
        "globalOptions": {
            "type": "object"
        },
        "fields": {
            "type": "array",
            "minItems" : 3,
            "items" : {
                "oneOf": [
                    { "$ref": "#/$defs/TaxonField" },
                    { "$ref": "#/$defs/SelectTaxonField" },
                    { "$ref": "#/$defs/PointJSONField" },
                    { "$ref": "#/$defs/GeoJSONField" },
                    { "$ref": "#/$defs/DecimalField" },
                    { "$ref": "#/$defs/FloatField" },
                    { "$ref": "#/$defs/IntegerField" },
                    { "$ref": "#/$defs/CharField" },
                    { "$ref": "#/$defs/ChoiceField" },
                    { "$ref": "#/$defs/MultipleChoiceField" },
                    { "$ref": "#/$defs/DateTimeJSONField" },
                    { "$ref": "#/$defs/BooleanField" },
                    { "$ref": "#/$defs/PictureField" }
                ]
            }
        },
        "taxonomicRestrictions": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/taxonomicRestriction"
            }
        },
        "taxonomicReference": {
            "description": "The uuid of the taxonomic reference field of this observation form"
        },
        "geographicReference": {
            "description": "The uuid of the geographic reference field of this observation form"
        },
        "temporalReference": {
            "description": "The uuid of the temporal reference field of this observation form"
        }
    },
    "required": [ "uuid", "version", "name", "slug", "fields", "taxonomicReference", "geographicReference",
                "temporalReference" ],

    "additionalProperties": False,

    "$defs": {
        "taxonomicRestriction": {
            "type": "object",
            "properties" : {
                "taxonSource": {
                    "type": "string"
                },
                "taxonLatname": {
                    "type": "string"
                },
                "taxonAuthor": {
                    "type": "string"
                },
                "nameUuid": {
                    "type": "string",
                    "format": "uuid"
                },
                "taxonNuid": {
                    "type": "string"
                },
                "restrictionType": {
                    "type": "string",
                    "enum": ["exists", "required", "optional"]
                }
            },
            "additionalProperties": False,
        },
        "FieldBase": {
            "type": "object",
            "properties": {
                "uuid": {
                    "type": "string",
                    "format": "uuid"
                },
                "version": {
                    "type": "integer"
                },
                "position": {
                    "type": "integer"
                },
                "taxonomicRestrictions": {
                    "type": "array",
                    "items" : {
                        "$ref": "#/$defs/taxonomicRestriction"
                    }
                }
            }
        },
        "FieldDefinitionBase": {
            "type": "object",
            "properties": {
                "required": {
                    "type": "boolean"
                },
                "isSticky": {
                    "type": "boolean"
                },
                "label": {
                    "type": "string"
                },
                "helpText": {
                    "oneOf": [
                        { "type": "string" },
                        { "type": "null" }
                    ]
                },
                "initial": {
                    
                }
            },
        },
        "TaxonField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["TaxonField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["taxonomicReference", "regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["BackboneTaxonAutocompleteWidget", "FixedTaxonWidget"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                },
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "SelectTaxonField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["SelectTaxonField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["taxonomicReference", "regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["SelectTaxonWidget"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                },
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "PointJSONField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["PointJSONField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["geographicReference", "regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["MobilePositionInput"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                },
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "GeoJSONField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["GeoJSONField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["geographicReference", "regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["PointOrAreaInput"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                },
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "DateTimeJSONField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["DateTimeJSONField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["temporalReference", "regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["SelectDateTimeWidget"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                },
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "CharField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["CharField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["TextInput", "Textarea"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                },
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "DecimalField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["DecimalField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["MobileNumberInput"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "number"
                        },
                        "max": {
                            "type": "number"
                        },
                        "step": {
                            "type": "number"
                        }
                    }
                }
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "FloatField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["FloatField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["MobileNumberInput"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "number"
                        },
                        "max": {
                            "type": "number"
                        },
                        "step": {
                            "type": "number"
                        }
                    }
                }
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "IntegerField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["IntegerField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["MobileNumberInput"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "integer"
                        },
                        "max": {
                            "type": "integer"
                        },
                        "step": {
                            "type": "integer"
                        }
                    }
                }
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "MultipleChoiceField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["MultipleChoiceField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["CheckboxSelectMultiple"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "choices": {
                    "type": "array"
                },
                "widgetAttrs": {
                    "type": "object"
                }
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "ChoiceField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["ChoiceField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["Select"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "choices": {
                    "type": "array"
                },
                "widgetAttrs": {
                    "type": "object"
                }
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "BooleanField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["BooleanField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["CheckboxInput"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                }
            },
            "required": ["uuid", "fieldClass", "version", "role", "definition", "position"]
        },
        "PictureField": {
            "type": "object",
            "allOf": [
                { "$ref": "#/$defs/FieldBase"}
            ],
            "properties": {
                "fieldClass": {
                    "type": "string",
                    "enum": ["PictureField"]
                },
                "role": {
                    "type": "string",
                    "enum": ["regular"]
                },
                "definition" : {
                    "type": "object",
                    "allOf" : [
                        { "$ref": "#/$defs/FieldDefinitionBase" }
                    ],
                    "properties": {
                        "widget": {
                            "type": "string",
                            "enum": ["CameraAndAlbumWidget"]
                        }
                    },
                    "required" : ["widget", "label"]
                },
                "widgetAttrs": {
                    "type": "object"
                }
            }
        }
    }
}

CRS_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["name"]
        },
        "properties": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": ["EPSG:4326"]
                }
            },
            "required": ["name"]
        }
    },
    "required": ["type", "properties"]
}


POINT_GEOMETRY_SCHEMA = {
    "type": "object",
    "properties": {
        "crs": CRS_SCHEMA,
        "type": {
            "type": "string",
            "enum": ["Point"],
        },
        "coordinates": {
            "type": "array",
            "items": {
                "type": "number"
            },
            "minContains": 2,
            "maxContains": 2
        }
    },
    "required": ["crs", "type", "coordinates"]
}

POLYGON_GEOMETRY_SCHEMA = {
    "type": "object",
    "properties": {
        "crs": CRS_SCHEMA,
        "type": {
            "type": "string",
            "enum": ["Polygon"],
        },
        "coordinates": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {
                        "type": "number",
                        "minContains": 2,
                        "maxContains": 2
                    }
                }
            }
        }
    },
    "required": ["crs", "type", "coordinates"]
}


POINT_JSON_FIELD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/point.schema.json",
    "title": "Point JSON Field",
    "description": "A geojson field for a point",
    "type": "object",
    "properties": {
        "type" : {
            "type": "string",
            "enum": ["Feature"]
        },
        "geometry": POINT_GEOMETRY_SCHEMA,
        "properties": {
            "type": "object",
            "properties": {
                "accuracy": {
                    "type": "number"
                }
            }
        }
    },
    "required": ["type", "geometry"]
}

GEOJSON_FIELD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/geojson.schema.json",
    "title": "GeoJSON Field",
    "description": "A geojson field for a point or a polygon",
    "type": "object",
    "properties": {
        "type" : {
            "type": "string",
            "enum": ["Feature"]
        },
        "geometry": {
            "anyOf": [POINT_GEOMETRY_SCHEMA, POLYGON_GEOMETRY_SCHEMA]
        }
    },
    "required": ["type", "geometry"]
}


TEMPORAL_JSON_FIELD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/temporal.schema.json",
    "title": "Temporal JSON Field",
    "description": "A json field representing data and or time",
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["Temporal"]
        },
        "cron": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["timestamp"]
                },
                "format": {
                    "type": "string",
                    "enum": ["unixtime"]
                },
                "timestamp": {
                    "type": "integer"
                },
                "timezoneOffset": {
                    "type": "integer"
                }
            },
            "required": ["type", "format", "timestamp", "timezoneOffset"]
        }
    },
    "required": ["type", "cron"]
}

TAXON_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://localcosmos.org/taxon.schema.json",
    "title": "Taxon Field",
    "description": "A json field representing a Taxon",
    "type": "object",
    "properties": {
        "taxonSource": {
            "type": "string"
        },
        "taxonLatname": {
            "type": "string"
        },
        "taxonAuthor": {
            "type": "string"
        },
        "taxonNuid": {
            "type": "string"
        },
        "nameUuid": {
            "type": "string"
        }
    },
    "required": ["taxonSource", "taxonLatname", "taxonNuid", "nameUuid"],
    "additionalProperties": False
}