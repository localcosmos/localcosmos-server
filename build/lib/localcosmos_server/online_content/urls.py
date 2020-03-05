from django.urls import path, re_path

from django.contrib.auth.decorators import login_required

from . import views


urlpatterns = [
    path('<str:app_uid>/manage-online-content/',
         login_required(views.ManageOnlineContent.as_view()), name='manage_onlinecontent'),
    path('<str:app_uid>/create-template-content/<str:template_type>/',
         login_required(views.CreateTemplateContent.as_view()), name='create_template_content'),
    path('<str:app_uid>/manage-template-content/<int:pk>/', login_required(views.ManageTemplateContent.as_view()),
        name='manage_template_content'),
    # translating template content
    path('<str:app_uid>/translate-template-content/<int:pk>/<str:language>/',
        login_required(views.TranslateTemplateContent.as_view()), name='translate_template_content'),
    # publishing template content
    path('<str:app_uid>/publish-template-content/<int:template_content_id>/',
        login_required(views.PublishTemplateContent.as_view()), name='publish_template_content'),
    path('<str:app_uid>/unpublish-template-content/<int:template_content_id>/',
        login_required(views.UnpublishTemplateContent.as_view()), name='unpublish_template_content'),
    # DELETING CONTENT
    path('<str:app_uid>/delete-templatecontent/<int:pk>/',
        login_required(views.DeleteTemplateContent.as_view()), name='delete_template_content'),
    path('<str:app_uid>/delete-microcontent/<int:template_content_id>/<str:language>/',
        login_required(views.DeleteMicroContent.as_view()), name='DeleteMicroContent'),
    path('<str:app_uid>/delete-filecontent/<int:template_content_id>/<str:language>/',
        login_required(views.DeleteFileContent.as_view()), name='DeleteFileContent'),
    # IMAGES - template content required
    path('<str:app_uid>/online-content/upload-image/<int:template_content_id>/<str:microcontent_category>/<str:microcontent_type>/<str:language>/',
        login_required(views.UploadImage.as_view()), name='upload_image'),
    # LICENCED IMAGES
    # upload new image
    path('<str:app_uid>/online-content/upload-licenced-image/<int:template_content_id>/<str:microcontent_category>/<str:microcontent_type>/<str:language>/',
        login_required(views.ManageImageUpload.as_view()), name='upload_licenced_image'),
    # edit localized image or upload new locale
    path('<str:app_uid>/online-content/update-licenced-image/<int:template_content_id>/<str:microcontent_category>/<int:microcontent_id>/<str:language>/',
        login_required(views.ManageImageUpload.as_view()), name='update_licenced_image'),
    # GET EMPTY FIELDS
    path('<str:app_uid>/online-content/get-form-field/<int:template_content_id>/<str:microcontent_category>/<str:microcontent_type>/<str:language>/',
        login_required(views.GetFormField.as_view()), name='get_form_field'),
]
