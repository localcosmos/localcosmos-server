from django.test import TestCase
from django import forms

from localcosmos_server.datasets.forms import DatasetValidationRoutineForm, ObservationForm
from localcosmos_server.datasets.models import DatasetValidationRoutine, DATASET_VALIDATION_CHOICES

from localcosmos_server.tests.mixins import WithApp, WithValidationRoutine, WithObservationForm

from localcosmos_server.taxonomy.lazy import LazyAppTaxon
from localcosmos_server.utils import datetime_from_cron

from localcosmos_server.tests.common import test_settings, DataCreator

@test_settings
class TestDatasetValidationRoutineForm(WithApp, WithValidationRoutine, TestCase):

    @test_settings
    def test__init__no_instance_no_routine(self):

        # blank validation routine
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        form = DatasetValidationRoutineForm(validation_routine)

        self.assertEqual(len(form.fields['position'].choices), 1)
        self.assertEqual(form.validation_routine, validation_routine)

    @test_settings
    def test__init__no_instance(self):

        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        form = DatasetValidationRoutineForm(validation_routine)

        self.assertEqual(len(form.fields['position'].choices), 2)
        self.assertEqual(form.validation_routine, validation_routine)
        
    @test_settings
    def test__init__instance(self):

        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.filter(app=self.app)

        step = validation_routine.first()

        form = DatasetValidationRoutineForm(validation_routine, instance=step)

        self.assertEqual(len(form.fields['position'].choices), 1)
        self.assertEqual(form.instance, step)
        self.assertEqual(form.validation_routine, validation_routine)


    @test_settings
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

    @test_settings
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

    @test_settings
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


class TestObservationForm(WithObservationForm, WithApp, TestCase):


    def get_field_by_uuid(self, observation_form, field_uuid):

        for field in observation_form.definition['fields']:
            if field['uuid'] == field_uuid:
                return field

        return None

    @test_settings
    def test_all_fields(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        json_data = dataset.data

        form = ObservationForm(self.app, dataset)

        self.assertEqual(len(form.fields), len(json_data))

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
            json_field = self.get_field_by_uuid(observation_form, field.name)
            self.assertEqual(widget_class, json_field['definition']['widget'] )

            # check choices
            if field_class in choice_fields:

                definition_choices = json_field['definition']['choices']
                
                for index, choice in enumerate(definition_choices):
                    
                    field_choice = field.field.choices[index]
                    self.assertEqual(list(choice), list(field_choice))
                
    @test_settings
    def test_get_initial_from_dataset(self):

        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        form = ObservationForm(self.app, dataset)

        initial = form.get_initial_from_dataset(dataset)

        taxonomic_reference_uuid = observation_form.definition['taxonomicReference']
        temporal_reference_uuid = observation_form.definition['temporalReference']
        geographic_reference_uuid = observation_form.definition['geographicReference']

        for key, value in initial.items():

            self.assertIn(key, dataset.data)

            reported_value = dataset.data[key]

            if key == taxonomic_reference_uuid:
                # check the taxon
                self.assertEqual(value.taxon_source, reported_value['taxonSource'])
                self.assertEqual(value.taxon_latname, reported_value['taxonLatname'])
                self.assertEqual(value.name_uuid, reported_value['nameUuid'])
            elif key == temporal_reference_uuid:
                self.assertEqual(value, datetime_from_cron(reported_value))
            else:
                self.assertEqual(value, reported_value)
                    

            
