from django.utils.translation import gettext_lazy as _

from .forms import ExpertReviewValidationForm, HumanInteractionValidationForm

from .base import RequiredFieldsValidator, HumanInteractionValidator

'''
    A dataset can only be valid if it supplies the 3 reference fields:
    - Taxon
    - Location
    - Time
'''
class ReferenceFieldsValidator(RequiredFieldsValidator):

    verbose_name = _('Reference fields validator')
    description = _('Automatically checks if taxon, date/time, and location are given.')
    

class ExpertReviewValidator(HumanInteractionValidator):

    template_name = 'datasets/validation/expert_review.html'
    form_class = ExpertReviewValidationForm

    status_message = _('This observation is currently waiting for review.')

    verbose_name = _('Expert review')
    description = _('An expert will review the dataset. This validation can include the analysis of images.')


    def form_valid(self, dataset, view_instance, form):


        validation_result = form.cleaned_data['dataset_is_valid']

        if validation_result == 'is_valid':
            self.on_valid(dataset)

        else:
            error_message = self.error_message

            comment = form.cleaned_data['comment']

            self.add_error(error_message, comment)
            self.on_invalid(dataset)

        context = view_instance.get_context_data(**view_instance.kwargs)
        context['form'] = form
        context['review_success'] = True
        context['validation_result'] = validation_result
        return view_instance.render_to_response(context)
