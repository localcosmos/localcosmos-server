from typing import Any
from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.http import HttpResponse
from django.utils.encoding import smart_str

from localcosmos_server.decorators import ajax_required
from localcosmos_server.generic_views import AjaxDeleteView

from .forms import DatasetValidationRoutineForm, ObservationForm, AddDatasetImageForm

from .models import Dataset, DatasetValidationRoutine, DATASET_VALIDATION_CLASSES, DatasetImages

from .csv_export import DatasetCSVExport


class ListDatasets(TemplateView):

    template_name = 'datasets/list_datasets.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['datasets'] = Dataset.objects.filter(app_uuid=self.request.app.uuid)
        return context



class HumanInteractionValidationView(FormView):

    template_name = None
    observation_form_class = ObservationForm
    form_class = None

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.dataset = Dataset.objects.get(pk=kwargs['dataset_id'])
        self.validation_step = DatasetValidationRoutine.objects.get(pk=kwargs['validation_step_id'])

        ValidatorClass = self.validation_step.get_class()
        self.validator = ValidatorClass(self.validation_step)

        self.template_name = self.validator.template_name
        self.form_class = self.validator.form_class

        return super().dispatch(request, *args, **kwargs)

    def get_observation_form(self):
        return self.observation_form_class(self.request.app, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['observation_form'] = self.get_observation_form()
        context['dataset'] = self.dataset
        context['validation_step'] = self.validation_step
        return context

    def form_valid(self, form):
        return self.validator.form_valid(self.dataset, self, form)



class EditDataset(FormView):

    form_class = ObservationForm
    template_name = 'datasets/edit_dataset.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.dataset = Dataset.objects.get(pk=kwargs['dataset_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self):
        return self.form_class(self.request.app, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context
    

# an expert may change dataset values -> only dataset.data
class AjaxSaveDataset(FormView):
    
    form_class = ObservationForm
    template_name = 'datasets/validation/ajax/dataset_form.html'


    @method_decorator(ajax_required)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.dataset = Dataset.objects.get(pk=kwargs['dataset_id'])
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context


    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()

        return self.form_class(self.request.app, self.dataset, **self.get_form_kwargs())


    def form_valid(self, form):

        # only update dataset.data.reported_values
        reported_values = form.validated_dataset_data

        self.dataset.data = reported_values
        self.dataset.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


class AjaxLoadFormFieldImages(TemplateView):

    template_name = 'datasets/validation/ajax/picture_field_images.html'

    @method_decorator(ajax_required)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.dataset = Dataset.objects.get(pk=kwargs['dataset_id'])
        self.field_uuid = request.GET['field_uuid']
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        context['field_uuid'] = self.field_uuid
        images = DatasetImages.objects.filter(dataset=self.dataset, field_uuid=self.field_uuid)
        context['images'] = images
        return context


class LargeModalImage(TemplateView):
    
    template_name = 'datasets/validation/ajax/large_modal_image.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['image_url'] = self.request.GET['image_url']
        return context
    
    
class ShowDatasetValidationRoutine(TemplateView):

    template_name = 'datasets/dataset_validation_routine.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        validation_routine = DatasetValidationRoutine.objects.filter(app=self.request.app)
        context['dataset_validation_routine'] = validation_routine

        available_validation_classes = []

        for d in DATASET_VALIDATION_CLASSES:

            validation_class = {
                'verbose_name' : str(d.verbose_name),
                'description' : d.description,
            }

            available_validation_classes.append(validation_class)
            
        context['available_validation_classes'] = available_validation_classes
        
        return context


from localcosmos_server.view_mixins import TaxonomicRestrictionMixin
class ManageDatasetValidationRoutineStep(TaxonomicRestrictionMixin, FormView):

    template_name = 'datasets/manage_dataset_validation_routine_step.html'

    form_class = DatasetValidationRoutineForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.validation_routine = DatasetValidationRoutine.objects.filter(app=request.app)
        
        self.validation_step = None
        if 'pk' in kwargs:
            self.validation_step = DatasetValidationRoutine.objects.get(pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['instance'] = self.validation_step
        return form_kwargs


    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.validation_routine, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['validation_step'] = self.validation_step
        return context

    def get_initial(self):
        initial = super().get_initial()

        if self.validation_step:
            initial['validation_step'] = self.validation_step.validation_class
            initial['position'] = self.validation_step.position
            
        return initial
    
    # important: adjust position of all existing steps
    def form_valid(self, form):

        validation_class = form.cleaned_data['validation_step']
        position = form.cleaned_data['position']

        following_steps = DatasetValidationRoutine.objects.filter(app=self.request.app, position__gte=position)

        for step in following_steps:
            step.position = step.position+1
            step.save()


        if not self.validation_step:
            self.validation_step = DatasetValidationRoutine(
                app=self.request.app,
            )

        self.validation_step.validation_class = validation_class
        self.validation_step.position=position

        self.validation_step.save()

        # optionally store taxonomic restriction
        self.save_taxonomic_restriction(self.validation_step, form)

        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        context['validation_step'] = self.validation_step

        return self.render_to_response(context)


class DeleteDatasetValidationRoutineStep(AjaxDeleteView):

    model = DatasetValidationRoutine

    def get_deletion_message(self):
        return _('Do you really want to remove {0}?'.format(self.object.verbose_name()))



class DeleteDataset(AjaxDeleteView):

    template_name = 'datasets/validation/ajax/delete_dataset.html'

    model = Dataset

    def get_deletion_message(self):
        return _('Do you really want to delete this obsersavtion?')


class DeleteDatasetImage(AjaxDeleteView):

    template_name = 'datasets/validation/ajax/delete_dataset_image.html'

    model = DatasetImages

    def get_deletion_message(self):
        return _('Do you really want to delete this image?')



class CreateDownloadDatasetsCSV(TemplateView):
    
    template_name = 'datasets/ajax/download_datasets_csv.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['csv_file'] = None
        context['ready'] = False
        
        return context 
    
    def get(self, request, *args, **kwargs):
        
        # this could run in a thread
        csv_export = DatasetCSVExport(self.request.app)
        csv_export.write_csv()

        # couldnt get X-Sendfile to work with django, wsgi and nginx
        '''        
        response = HttpResponse(content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename=datasets.csv'
        
        filepath = smart_str('http://{0}{1}'.format(request.get_host(), csv_export.url))
        
        response['X-Sendfile'] = filepath
        response['X-Accel-Redirect'] = filepath
        # It's usually a good idea to set the 'Content-Length' header too.
        # You can also set any other required headers: Cache-Control, etc.
        '''
        
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)
    
    
class DownloadDatasetsCSV(TemplateView):
    
    template_name = 'datasets/ajax/download_datasets_csv_button.html'
    
    def get_context_data(self, **kwargs):
        csv_export = DatasetCSVExport(self.request.app)
        
        context = super().get_context_data(**kwargs)
        context['ready'] = True
        context['csv_url'] = csv_export.url
        return context

    @method_decorator(ajax_required)
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class AddDatasetImage(FormView):

    template_name = 'datasets/validation/ajax/add_dataset_image.html'
    form_class = AddDatasetImageForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_dataset(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_dataset(self, **kwargs):
        self.dataset = Dataset.objects.get(pk=kwargs['dataset_id'])
        self.image_field_uuid=kwargs['image_field_uuid']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        context['image_field_uuid'] = self.image_field_uuid
        context['success'] = False
        return context

    def form_valid(self, form):
        
        image_file = form.cleaned_data['image']

        dataset_image = DatasetImages(
            dataset = self.dataset,
            field_uuid = self.image_field_uuid,
            image = image_file,
        )

        dataset_image.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True

        return self.render_to_response(context)

