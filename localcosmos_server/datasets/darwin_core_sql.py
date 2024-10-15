from django.conf import settings

def get_darwin_core_view_name(app):
    return '{0}_datasets_darwin_core'.format(app.uid)


'''
    getting taxonRank is impossible because the taxonomy is not present as a database
    currently, only taxa present in the catalogue of life are listed
    the full scientific name with author is supported
'''
def get_darwin_core_view_create_sql(app):
    
    view_name = get_darwin_core_view_name(app)
    
    sql = '''CREATE OR REPLACE VIEW {0} as SELECT 
        dd.uuid AS "occurrenceID", 
        'HumanObservation' AS "basisOfRecord", 
        dd.timestamp AS "eventDate",
        concat_ws(' ', dd.taxon_latname, dd.taxon_author) AS "scientificName",
        ST_Y(ST_Transform(dd.coordinates, 4326)) AS "decimalLatitude", 
        ST_X(ST_Transform(dd.coordinates, 4326)) AS "decimalLongitude", 
        'EPSG:4326' AS "geodeticDatum"
        FROM
        datasets_dataset dd WHERE dd.app_uuid='{1}' AND dd.taxon_source='taxonomy.sources.col';
    '''.format(view_name, str(app.uuid))
    return sql


def get_darwin_core_view_drop_sql(app):
    view_name = get_darwin_core_view_name(app)
    sql = 'DROP VIEW IF EXISTS {0}'.format(view_name)
    return sql


def get_darwin_core_view_exists_sql(app, schema_name):

    view_name = get_darwin_core_view_name(app)
    sql = '''SELECT EXISTS (SELECT FROM INFORMATION_SCHEMA.VIEWS WHERE table_schema='{0}' AND table_name='{1}') '''.format(schema_name, view_name)
    return sql