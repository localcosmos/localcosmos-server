from django.test import TestCase
from django import forms

from localcosmos_server.datasets.forms import DatasetValidationRoutineForm, ObservationForm
from localcosmos_server.datasets.models import DatasetValidationRoutine, DATASET_VALIDATION_CHOICES

from localcosmos_server.tests.mixins import WithApp, WithValidationRoutine

from localcosmos_server.taxonomy.lazy import LazyAppTaxon
from localcosmos_server.utils import datetime_from_cron

from localcosmos_server.tests.common import test_settings, TEST_DATASET_FULL_GENERIC_FORM

@test_settings
class TestDatasetValidationRoutineForm(WithApp, WithValidationRoutine, TestCase):

    def test__init__no_instance_no_routine(self):

        # blank validation routine
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        form = DatasetValidationRoutineForm(validation_routine)

        self.assertEqual(len(form.fields['position'].choices), 1)
        self.assertEqual(form.validation_routine, validation_routine)


    def test__init__no_instance(self):

        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        form = DatasetValidationRoutineForm(validation_routine)

        self.assertEqual(len(form.fields['position'].choices), 2)
        self.assertEqual(form.validation_routine, validation_routine)
        

    def test__init__instance(self):

        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        step = validation_routine.first()

        form = DatasetValidationRoutineForm(validation_routine, instance=step)

        self.assertEqual(len(form.fields['position'].choices), 1)
        self.assertEqual(form.instance, step)
        self.assertEqual(form.validation_routine, validation_routine)


    def test_clean_validation_step_no_routine_no_instance(self):
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        data = {
            'validation_step' : DATASET_VALIDATION_CHOICES[0][0],
            'position': 1,
        }
        
        form = DatasetValidationRoutineForm(validation_routine, data=data)
        form.cleaned_data = data

        validation_step = form.clean_validation_step()
        self.assertEqual(validation_step, data['validation_step'])


    def test_clean_validation_step_routine_no_instance(self):

        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        data = {
            'validation_step' : DATASET_VALIDATION_CHOICES[0][0],
            'position': 1,
        }
        
        form = DatasetValidationRoutineForm(validation_routine, data=data)
        form.cleaned_data = data

        with self.assertRaises(forms.ValidationError):
            validation_step = form.clean_validation_step()


    def test_clean_validation_step_routine_with_instance(self):

        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app).order_by('position')

        data = {
            'validation_step' : DATASET_VALIDATION_CHOICES[0][1],
            'position': 1,
        }

        step = validation_routine.first()
        
        form = DatasetValidationRoutineForm(validation_routine, data=data, instance=step)
        form.cleaned_data = data

        validation_step = form.clean_validation_step()
        self.assertEqual(validation_step, data['validation_step'])



WIDGET_MAP = {
    'TaxonAutocompleteWidget' : 'BackboneTaxonAutocompleteWidget',
}

@test_settings
class TestObservationForm(WithApp, TestCase):

    def get_field_by_uuid(self, fields, field_uuid):

        for field in fields:
            if field['uuid'] == field_uuid:
                return field

        return None

    def test_all_fields(self):

        dataset_json = TEST_DATASET_FULL_GENERIC_FORM

        json_form_fields = dataset_json['dataset']['observation_form']['fields']


        form = ObservationForm(self.app, dataset_json)

        self.assertEqual(len(form.fields), len(json_form_fields))

        choice_fields = ['ChoiceField', 'MultipleChoiceField']

        for field in form:

            self.assertFalse(field.field.required)

            field_class = field.field.__class__.__name__

            if field_class in form.locked_field_classes:
                self.assertTrue(field.field.widget.attrs['readonly'])

            else:
                self.assertFalse(field.field.widget.attrs.get('readonly', False))


            widget_class = field.field.widget.__class__.__name__
            if widget_class in WIDGET_MAP:
                widget_class = WIDGET_MAP[widget_class]
            json_field = self.get_field_by_uuid(json_form_fields, field.name)
            self.assertEqual(widget_class, json_field['definition']['widget'] )

            # check choices
            if field_class in choice_fields:

                definition_choices = json_field['definition']['choices']
                self.assertEqual(definition_choices, field.field.choices)
                
    
    def test_get_initial_from_dataset(self):

        dataset_json = TEST_DATASET_FULL_GENERIC_FORM

        form = ObservationForm(self.app, dataset_json)

        initial = form.get_initial_from_dataset(dataset_json['dataset'])

        taxonomic_reference_uuid = dataset_json['dataset']['observation_form']['taxonomic_reference']
        temporal_reference_uuid = dataset_json['dataset']['observation_form']['temporal_reference']
        geographic_reference_uuid = dataset_json['dataset']['observation_form']['geographic_reference']

        for key, value in initial.items():

            self.assertIn(key, dataset_json['dataset']['reported_values'])

            reported_value = dataset_json['dataset']['reported_values'][key]

            if key == taxonomic_reference_uuid:
                # check the taxon
                self.assertEqual(value.taxon_source, reported_value['taxon_source'])
                self.assertEqual(value.taxon_latname, reported_value['taxon_latname'])
                self.assertEqual(value.name_uuid, reported_value['name_uuid'])
            elif key == temporal_reference_uuid:
                self.assertEqual(value, datetime_from_cron(reported_value))
            else:
                self.assertEqual(value, reported_value)
                    

            
