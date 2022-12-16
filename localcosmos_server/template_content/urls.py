from django.urls import path, re_path

from django.contrib.auth.decorators import login_required

from . import views


urlpatterns = [
    path('<str:app_uid>/template-content-list/',
         login_required(views.TemplateContentList.as_view()), name='template_content_home'),
    path('<str:app_uid>/create-template-content/<str:template_type>/',
         login_required(views.CreateTemplateContent.as_view()), name='create_template_content'),
     path('<str:app_uid>/manage-localized-template-content/<int:localized_template_content_id>/',
          login_required(views.ManageLocalizedTemplateContent.as_view()),
          name='manage_localized_template_content'),
     path('<str:app_uid>/delete-templatecontent/<int:pk>/',
        login_required(views.DeleteTemplateContent.as_view()), name='delete_template_content'),
     # translating
     path('<str:app_uid>/translate-template-content/<int:template_content_id>/<str:language>/',
        login_required(views.TranslateTemplateContent.as_view()), name='translate_template_content'),
     # images
     path('manage-template-content-image/<int:content_image_id>/',
          views.ManageTemplateContentImage.as_view(), name='manage_template_content_image'),
     path('manage-template-content-image/<int:content_type_id>/<int:object_id>/<str:image_type>/',
          views.ManageTemplateContentImage.as_view(),
        name='manage_template_content_image'),
     path('delete-template-content-image/<int:pk>/',
        views.DeleteTemplateContentImage.as_view(), name='delete_template_content_image'),
     path('get-template-content-formfields/<int:localized_template_content_id>/<str:content_key>/',
        views.GetTemplateContentFormFileFields.as_view(), name='get_template_content_form_fields'),
     # publishing and unpublishing template content
     path('<str:app_uid>/publish-template-content/<int:template_content_id>/',
          login_required(views.PublishTemplateContent.as_view()), name='publish_template_content'),
     path('<str:app_uid>/unpublish-template-content/<int:template_content_id>/',
        login_required(views.UnpublishTemplateContent.as_view()), name='unpublish_template_content'),
]
