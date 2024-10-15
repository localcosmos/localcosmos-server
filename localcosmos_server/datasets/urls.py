from django.urls import path

from . import views

app_name = 'datasets'

urlpatterns = [
    path('<str:app_uid>/datasets/', views.ListDatasets.as_view(), name='list_datasets'),
    path('<str:app_uid>/datasets/csv/', views.DownloadDatasetsCSV.as_view(), name='download_datasets_csv'),
    path('<str:app_uid>/datasets/create-csv/', views.CreateDownloadDatasetsCSV.as_view(), name='create_download_datasets_csv'),
    path('<str:app_uid>/dataset/<int:dataset_id>/edit/', views.EditDataset.as_view(), name='edit_dataset'),
    path('<str:app_uid>/dataset-validation-routine/', views.ShowDatasetValidationRoutine.as_view(),
        name='dataset_validation_routine'),
    path('<str:app_uid>/manage-dataset-validation-routine-step/',
        views.ManageDatasetValidationRoutineStep.as_view(), name='add_dataset_validation_routine_step'),
    path('<str:app_uid>/manage-dataset-validation-routine-step/<int:pk>/',
        views.ManageDatasetValidationRoutineStep.as_view(), name='manage_dataset_validation_routine_step'),
    path('<str:app_uid>/delete-dataset-validation-routine-step/<int:pk>/',
        views.DeleteDatasetValidationRoutineStep.as_view(), name='delete_dataset_validation_routine_step'),
    path('<str:app_uid>/human-validation-routine-step/<int:dataset_id>/<int:validation_step_id>/',
        views.HumanInteractionValidationView.as_view(), name='human_validation'),
    path('<str:app_uid>/save-dataset/<int:dataset_id>/',
        views.AjaxSaveDataset.as_view(), name='save_dataset'),
    path('<str:app_uid>/get-field-images/<int:dataset_id>/',
        views.AjaxLoadFormFieldImages.as_view(), name='load_form_field_images'),
    path('<str:app_uid>/large-modal-image/',
        views.LargeModalImage.as_view(), name='large_modal_image'),
    # delete views
    path('<str:app_uid>/delete-dataset/<int:pk>/',
        views.DeleteDataset.as_view(), name='delete_dataset'),
    path('<str:app_uid>/delete-dataset-image/<int:pk>/',
        views.DeleteDatasetImage.as_view(), name='delete_dataset_image'),
    #add image
    path('<str:app_uid>/dataset/<int:dataset_id>/add-image/<str:image_field_uuid>/',
        views.AddDatasetImage.as_view(), name='add_dataset_image'),
    # taxon search
    path('<str:app_uid>/search-dataset-taxon/', views.SearchDatasetTaxon.as_view(), name='search_dataset_taxon'),
    # darwin core
    path('<str:app_uid>/gbif/', views.ManageDarwinCoreView.as_view(), name='manage_darwin_core'),
    path('<str:app_uid>/gbif/enable/', views.EnableDarwinCoreView.as_view(), name='enable_darwin_core'),
    path('<str:app_uid>/gbif/disable/', views.DisableDarwinCoreView.as_view(), name='disable_darwin_core'),
]
