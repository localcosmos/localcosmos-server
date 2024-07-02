from django.conf import settings
import csv, os, json

from localcosmos_server.utils import datetime_from_cron

from localcosmos_server.datasets.models import Dataset, DatasetImages

class DatasetCSVExport:

    def __init__(self, app, filters={}):

        filters['app_uuid'] = app.uuid
        
        dir_name = 'exports'
        filename = 'datasets.csv'

        self.csv_dir = os.path.join(app.media_base_path, dir_name)
        self.filepath =  os.path.join(self.csv_dir, filename)
        
        self.url = os.path.join(app.media_base_url, dir_name, filename)
        
        self.filters = filters
        

    def get_queryset(self):
        return Dataset.objects.filter(**self.filters)
    
    
    def get_PointJSONField_coordinate_label(self, coordinate, label):
        return '{0} ({1})'.format(label, coordinate)
    
    def get_PointJSONField_coordinate_uuid(self, coordinate, field_uuid):
        return '{0}_{1}'.format(field_uuid, coordinate)

    def write_csv(self):

        if not os.path.isdir(self.csv_dir):
            os.makedirs(self.csv_dir)

        if os.path.isfile(self.filepath):
            os.remove(self.filepath)

        columns = ['client_id', 'platform']

        uuid_to_label = {
            'client_id' : 'client_id',
            'platform' : 'platform',
        }

        field_classes = {
            'client_id' : 'CharField',
            'platform' : 'CharField',
        }

        for dataset in self.get_queryset():

            observation_form = dataset.observation_form

            for field in observation_form.definition['fields']:

                label = field['definition']['label']
                field_uuid = field['uuid']
                field_class = field['fieldClass']
                
                # split point coordinates into two columns
                if field_class == 'PointJSONField':
                    field_uuid_x = self.get_PointJSONField_coordinate_uuid('x', field_uuid)
                    field_uuid_y = self.get_PointJSONField_coordinate_uuid('y', field_uuid)
                    
                    label_x = self.get_PointJSONField_coordinate_label('x', label)
                    label_y = self.get_PointJSONField_coordinate_label('y', label)
                    
                    uuid_to_label[field_uuid_x] = label_x
                    uuid_to_label[field_uuid_y] = label_y
                    
                    columns.append(label_x)
                    columns.append(label_y)
                
                else:
                
                    # merge field_uuids that have the same label
                    # e.g. someone deletes and recreates a field
                    if field_uuid not in uuid_to_label:
                        uuid_to_label[field_uuid] = label

                    if label not in columns:
                        columns.append(label)
                    

                field_classes[field_uuid] = field_class

        # write the csv header row
        with open(self.filepath, 'w', newline='') as csvfile:
            dataset_writer = csv.writer(csvfile, delimiter='|')
            dataset_writer.writerow(columns)

            for dataset in self.get_queryset():

                reported_data = dataset.data

                data_columns = [None]*len(columns)
                
                data_columns[0] = dataset.client_id
                data_columns[1] = dataset.platform

                for field_uuid, value in reported_data.items():

                    field_class = field_classes[field_uuid]
                    serialize_fn_name = 'serialize_{0}'.format(field_class)

                    if hasattr(self, serialize_fn_name):
                        serialize_fn = getattr(self, serialize_fn_name)
                        value = serialize_fn(value)
                    
                    if field_class == 'PointJSONField':
                        
                        field_uuid_x = self.get_PointJSONField_coordinate_uuid('x', field_uuid)
                        field_uuid_y = self.get_PointJSONField_coordinate_uuid('y', field_uuid)
                        
                        label_x = uuid_to_label[field_uuid_x]
                        label_y = uuid_to_label[field_uuid_y]
                        
                        value_x = None
                        value_y = None
                        
                        if value:
                            value_x = value[0]
                            value_y = value[1]
                        
                        data_columns[columns.index(label_x)] = value_x
                        data_columns[columns.index(label_y)] = value_y
                    
                    elif field_class == 'PictureField':
                        
                        label = uuid_to_label[field_uuid]
                        
                        images = DatasetImages.objects.filter(field_uuid=field_uuid)
                        
                        if images:
                            image_urls = []
                            for image in images:
                                image_urls.append(image.image.url)

                            value = ','.join(image_urls)
                            data_columns[columns.index(label)] = value
                    
                    else:

                        label = uuid_to_label[field_uuid]
                        data_columns[columns.index(label)] = value

                    
                dataset_writer.writerow(data_columns)
                

    def serialize_TaxonField(self, value):
        if value:
            return '{0} {1}'.format(value['taxonLatname'], value['taxonAuthor'])
        return value
    
    
    def serialize_SelectTaxonField(self, value):
        return self.serialize_TaxonField(value)
    

    def serialize_PointJSONField(self, value):
        if value:
            return value['geometry']['coordinates']
        return value
    
    
    def serialize_DateTimeJSONField(self, value):

        if value:
            dt = datetime_from_cron(value)
            return dt.isoformat()
        return value
    
    
    def serialize_MultipleChoiceField(self, value):
        if value and type(value) == list:
            return ','.join(value)
        return value  
    
    
    def serialize_ChoiceField(self, value):
        return value
    
    
    def serialize_CharField(self, value):
        return value
    
    
    def serialize_GeoJSONField(self, value):
        return json.dumps(value)
    
    def serialize_BooleanField(self, value):
        return value
    
    
    def serialize_DecimalField(self, value):
        return value
    
    
    def serialize_FloatField(self, value):
        return value
    
    
    def serialize_IntegerField(self, value):
        return value
    
    
    def serialize_PictureField(self, value):
        if value:
            raise ValueError('Not implemented: PictureField')
        return value
    
            
        
