from django import forms

from localcosmos_server.forms import LocalizeableModelForm

from localcosmos_server.achievements.factor_types import (
	FACTOR_DATASET_CREATED,
	FACTOR_GEOGRAPHY,
	FACTOR_IS_FIRST_DATASET_FOR_USER,
	FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER,
	FACTOR_TYPE_LABELS,
	OBJECT_MODELS_BY_FACTOR_TYPE,
)
from localcosmos_server.achievements.models import PointRule
from localcosmos_server.achievements.models import PointRuleCondition



class PointRuleForm(LocalizeableModelForm):

	valid_from = forms.DateTimeField(
		required=False,
		input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'],
		widget=forms.DateTimeInput(
			format='%Y-%m-%dT%H:%M',
			attrs={
				'type': 'datetime-local',
				'step': 60,
			},
		),
	)
	valid_to = forms.DateTimeField(
		required=False,
		input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'],
		widget=forms.DateTimeInput(
			format='%Y-%m-%dT%H:%M',
			attrs={
				'type': 'datetime-local',
				'step': 60,
			},
		),
	)
	
	localizeable_fields = ['awarded_for']
    
	class Meta:
		model = PointRule
		fields = (
			'name',
			'points',
			'awarded_for',
			'is_active',
			'match_mode',
			'valid_from',
			'valid_to',
		)
		help_texts = {
			'name': 'Internal admin label for this rule (used in management screens), e.g. "First taxon in region".',
			'points': 'Number of points awarded when all conditions of this rule are met.',
			'awarded_for': 'User-facing message explaining why points were awarded, e.g. "First sighting in this area".',
			'is_active': 'Inactive rules are never evaluated. Use this to pause a rule without deleting it.',
			'match_mode': '"All" requires every condition to match; "Any" awards points when at least one condition matches.',
			'valid_from': 'Optional. The rule will not be evaluated before this date and time.',
			'valid_to': 'Optional. The rule will not be evaluated after this date and time.',
		}

	def clean(self):
		cleaned_data = super().clean()
		valid_from = cleaned_data.get('valid_from')
		valid_to = cleaned_data.get('valid_to')

		if valid_from and valid_to and valid_from > valid_to:
			self.add_error('valid_to', 'valid_to must be greater than or equal to valid_from.')

		return cleaned_data


dataset_factor_choices = (
	(FACTOR_IS_FIRST_DATASET_FOR_USER, FACTOR_TYPE_LABELS[FACTOR_IS_FIRST_DATASET_FOR_USER]),
	(FACTOR_DATASET_CREATED, FACTOR_TYPE_LABELS[FACTOR_DATASET_CREATED]),
)

geography_factor_choices = (
	(FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER, FACTOR_TYPE_LABELS[FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER]),
	(FACTOR_GEOGRAPHY, FACTOR_TYPE_LABELS[FACTOR_GEOGRAPHY]),
)

class DatasetConditionForm(forms.Form):
    
    factor_type = forms.ChoiceField(choices=dataset_factor_choices)

class TaxonConditionForm(forms.Form):
	pass


class GeographyConditionForm(forms.Form):
	factor_type = forms.ChoiceField(choices=geography_factor_choices)
	geography = forms.ModelChoiceField(queryset=PointRule.objects.none(), required=False, empty_label='---------')

	def __init__(self, *args, **kwargs):
		app = kwargs.pop('app', None)
		super().__init__(*args, **kwargs)

		selected_factor_type = self._selected_factor_type()
		allowed_models = OBJECT_MODELS_BY_FACTOR_TYPE.get(selected_factor_type, ())

		if allowed_models:
			geography_model = allowed_models[0]
			queryset = geography_model.objects.all().order_by('name', 'pk')

			if app is not None and hasattr(geography_model, 'app_id'):
				queryset = queryset.filter(app=app)

			self.fields['geography'].queryset = queryset
		else:
			# No geography-selectable model for this factor.
			self.fields['geography'].queryset = self._empty_geography_queryset()

	def _selected_factor_type(self):
		if self.is_bound:
			return self.data.get('factor_type')

		if self.initial.get('factor_type'):
			return self.initial.get('factor_type')

		return FACTOR_GEOGRAPHY

	def _empty_geography_queryset(self):
		geography_models = OBJECT_MODELS_BY_FACTOR_TYPE.get(FACTOR_GEOGRAPHY, ())
		if geography_models:
			return geography_models[0].objects.none()

		return PointRule.objects.none()

	def clean(self):
		cleaned_data = super().clean()
		factor_type = cleaned_data.get('factor_type')
		geography = cleaned_data.get('geography')

		if factor_type == FACTOR_IS_FIRST_SPECIES_IN_POLYGON_FOR_USER and geography is not None:
			self.add_error('geography', 'This factor is only valid when no geography is selected.')

		return cleaned_data