from django.utils.translation import gettext_lazy as _

from localcosmos_server.taxonomy.lazy import LazyAppTaxon
'''
    a validator class consists of one method:
    - validate
'''

class DatasetValidatorBase:

    is_automatic = True

    def __init__(self, validation_routine_step):
        self.errors = []

        # db instance of this step, required for eg checking taxonomic restrictions
        self.validation_routine_step = validation_routine_step


    def set_dataset_validation_step_to_next(self, dataset):
        validation_routine = dataset.validation_routine
        validation_steps = list(validation_routine.values_list('validation_class', flat=True))

        index_count = len(validation_steps) -1

        next_index = validation_steps.index(self.validation_routine_step.validation_class) + 1

        if next_index <= index_count:
            next_step = validation_steps[next_index]
        else:
            next_step = 'completed'
            if not dataset.validation_errors:
                dataset.is_valid = True
            
        dataset.validation_step = next_step
        dataset.save()


    def check_taxonomic_restriction(self, dataset):

        taxonomic_restrictions = self.validation_routine_step.taxonomic_restrictions.all()
        lazy_taxon = LazyAppTaxon(instance=dataset)

        taxon_applies = lazy_taxon.check_restrictions(taxonomic_restrictions)

        return taxon_applies
        

    def run_validation(self, dataset):
        raise NotImplementedError('DatasetValidators require a run_validation() method')

    # non-automatic validators do not validate by method
    def validate(self, dataset):
        applies = self.check_taxonomic_restriction(dataset)

        if applies == True:
            self.run_validation(dataset)
        else:
            self.set_dataset_validation_step_to_next(dataset)
    
    
    def add_error(self, message, comment=None):
        error_obj = {
            'validator_name' : str(self.verbose_name),
            'validation_class' : str(self.validation_routine_step.validation_class),
            'message' : str(message),
            'comment' : comment,
        }
        
        self.errors.append(error_obj)


    def on_valid(self, dataset):
        # set to the next step
        self.set_dataset_validation_step_to_next(dataset)

        # continue validation
        dataset.validate()

    def on_invalid(self, dataset):

        errors = []
        if dataset.validation_errors:
            errors = dataset.validation_errors

        validation_errors = errors + self.errors

        dataset.validation_errors = validation_errors
        # set to next step
        self.set_dataset_validation_step_to_next(dataset)

        # continue validation
        dataset.validate()



# human interaction, validate() will return a rendered template
class HumanInteractionValidator(DatasetValidatorBase):
    
    is_automatic = False

    template_name = None
    form_class = None
    
    status_message = _('This dataset is currently waiting for review.')
    error_message = _('This dataset failed the review.')

    # no automatic validation
    def run_validation(self, dataset):
        pass


    def form_valid(self, view_instance, form):
        raise NotImplementedError('HumanInteractionValidator requires a form_valid method')
        


# this should be enhanced somehow to cover required fields in generic_forms etc
# maybe read required fields from dataset
class RequiredFieldsValidator(DatasetValidatorBase):

    required = []

    def validate(self, dataset):
        
        is_valid = True

        missing_fields = []

        for field in self.required:
            if not hasattr(dataset, field) or getattr(dataset, field) == None:
                is_valid = False
                missing_fields.append(field)

        if is_valid == False:
            error_message = _('The following fields are required but missing: ')
            error_message = error_message + ",".join(missing_fields)
            self.add_error(error_message)
            self.on_fail()

        else:
            self.on_success()
            
        self.validated = is_valid

        

'''
    DatasetJSONValidator
    - validates the given json, version specific
    - should be required for all LC datasets
    - see localcosmos/specifications for DatasetJSON specs
'''
class DatasetJSONValidator(DatasetValidatorBase):
    
    def validate(self, dataset):

        reported_values = dataset.data['dataset']['reported_values']
        
        if 'client_id' not in reported_values:
            raise ValueError('Dataset needs a client_id in dataset["reported_values"]')
    
        
        
