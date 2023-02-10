from django.conf import settings
import csv, os, json

from localcosmos_server.utils import datetime_from_cron

from localcosmos_server.datasets.models import Dataset

class DatasetCSVExport:

    def __init__(self, app, filters={}):

        filters['app_uuid'] = app.uuid

        self.csv_dir = os.path.join(app.media_base_path, 'exports')
        self.filepath =  os.path.join(self.csv_dir, 'datasets.csv')
        
        self.filters = filters
        

    def get_queryset(self):
        return Dataset.objects.filter(**self.filters)


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

            observation_form = dataset.data['dataset']['observation_form']

            for field in observation_form['fields']:

                label = field['definition']['label']
                field_uuid = field['uuid']

                # merge field_uuids that have the same label
                # e.g. someone deletes and recreates a field
                if field_uuid not in uuid_to_label:
                    uuid_to_label[field_uuid] = label

                if label not in columns:
                    columns.append(label)

                field_classes[field_uuid] = field['field_class']

        # write the csv header row
        with open(self.filepath, 'w', newline='') as csvfile:
            dataset_writer = csv.writer(csvfile, delimiter='|')
            dataset_writer.writerow(columns)

            for dataset in self.get_queryset():

                reported_data = dataset.data['dataset']['reported_values']

                data_column = [None]*len(columns)

                for field_uuid, value in reported_data.items():

                    field_class = field_classes[field_uuid]
                    serialize_fn_name = 'serialize_{0}'.format(field_class)

                    if hasattr(self, serialize_fn_name):
                        serialize_fn = getattr(self, serialize_fn_name)
                        value = serialize_fn(value)
                        

                    label = uuid_to_label[field_uuid]
                    data_column[columns.index(label)] = value

                    
                dataset_writer.writerow(data_column)
                

    def serialize_TaxonField(self, value):
        if value:
            return value['taxon_latname']
        return value

    def serialize_PointJSONField(self, value):
        if value:
            return json.dumps(value)
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
            
        
