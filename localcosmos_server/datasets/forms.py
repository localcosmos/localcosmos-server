from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from localcosmos_server.taxonomy.lazy import LazyAppTaxon
from localcosmos_server.utils import datetime_from_cron

from .models import DATASET_VALIDATION_CHOICES

from . import fields, widgets

import json


class DatasetValidationRoutineForm(forms.Form):

    validation_step = forms.ChoiceField(choices=DATASET_VALIDATION_CHOICES)
    position = forms.ChoiceField(choices=())

    def __init__(self, validation_routine, **kwargs):

        self.validation_routine = validation_routine

        self.instance = kwargs.pop('instance', None)

        super().__init__(**kwargs)

        if self.instance:
            self.fields['validation_step'].widget.attrs['readonly'] = True

        existing_steps = validation_routine.count()

        choices = []

        max_position = existing_steps + 2
        if self.instance:
            max_position = existing_steps + 1

        for i in range(1, max_position):
            choices.append((i,i))

        self.fields['position'].choices = choices
        

    def clean_validation_step(self):

        validation_step = self.cleaned_data['validation_step']

        existing_validation_steps = self.validation_routine.values_list('validation_class', flat=True)

        if validation_step in existing_validation_steps and not self.instance:
            raise forms.ValidationError(_('This step already exists in your Validation Routine'))

        return validation_step


'''
    Create an observation Form from dataset
'''
class ObservationForm(forms.Form):

    # fields that cannot be edited
    locked_field_roles = ['temporal_reference', 'geographic_reference']
    locked_field_classes = ['DateTimeJSONField', 'PointJSONField', 'PictureField']
    #locked_field_widget_classes = ['MobilePositionInput', 'CameraAndAlbumWidget', 'SelectDateTimeWidget']

    locked_field_uuids = []

    def __init__(self, app, observation_form_json, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial = self.get_initial_from_dataset(observation_form_json['dataset'])
        
        form_fields = observation_form_json['dataset']['observation_form']['fields']

        self.taxon_search_url = reverse('search_app_taxon', kwargs={'app_uid':app.uid})


        for form_field in form_fields:

            field_class_name = form_field['field_class']
            widget_class_name = form_field['definition']['widget']


            FieldClass = getattr(fields, field_class_name)
            WidgetClass = getattr(widgets, widget_class_name)

            widget_kwargs = {
                'attrs' : {},
            }

            field_kwargs = {
                'label' : form_field['definition']['label'],
                'required' : False,
            }

            kwargs_method_name = 'get_{0}_field_kwargs'.format(field_class_name)
            if hasattr(self, kwargs_method_name):
                method = getattr(self, kwargs_method_name)
                field_kwargs.update(method(form_field))


            if field_class_name == 'TaxonField':
                widget_kwargs['taxon_search_url'] = self.taxon_search_url
                # set to a bogus value to not display taxonomic source selection
                widget_kwargs['fixed_taxon_source'] = 'apptaxa'

            # lock certain fields
            if field_class_name in self.locked_field_classes or form_field['role'] in self.locked_field_roles:
                
                self.locked_field_uuids.append(form_field['uuid'])
                
                widget_kwargs['attrs'].update({
                    'readonly' : True,
                })
                

            if widget_class_name == 'CameraAndAlbumWidget':
                widget_kwargs['attrs']['load_images'] = True


            field_kwargs['widget'] = WidgetClass(**widget_kwargs)

            self.fields[form_field['uuid']] = FieldClass(**field_kwargs)


    def get_initial_from_dataset(self, dataset_json):
        
        initial = {}

        taxonomic_reference_uuid = dataset_json['observation_form']['taxonomic_reference']
        temporal_reference_uuid = dataset_json['observation_form']['temporal_reference']
        geographic_reference_uuid = dataset_json['observation_form']['geographic_reference']

        for key, value in dataset_json['reported_values'].items():

            if key == taxonomic_reference_uuid:
                initial[key] = LazyAppTaxon(**value)
            elif key == temporal_reference_uuid:
                initial[key] = datetime_from_cron(value)
            elif key == geographic_reference_uuid:
                initial[key] = value
            else:
                initial[key] = value
                
        return initial


    def get_TaxonField_field_kwargs(self, form_field):
        kwargs = {
            'taxon_search_url' : self.taxon_search_url,
        }

        return kwargs
        

    def get_ChoiceField_field_kwargs(self, form_field):

        kwargs = {
            'choices' : form_field['definition']['choices'],
        }

        return kwargs


    def get_MultipleChoiceField_field_kwargs(self, form_field):

        kwargs = {
            'choices' : form_field['definition']['choices'],
        }

        return kwargs
