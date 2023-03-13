from django.urls import path

from django.contrib.auth.decorators import login_required

from . import views


urlpatterns = [
   path('<str:app_uid>/template-content-list/', views.TemplateContentList.as_view(), name='template_content_home'),
   path('<str:app_uid>/create-template-content/<str:template_type>/', views.CreateTemplateContent.as_view(),
      name='create_template_content'),
   path('<str:app_uid>/create-template-content/<str:template_type>/<str:assignment>/',
      views.CreateTemplateContent.as_view(), name='create_template_content'),
   path('<str:app_uid>/manage-localized-template-content/<int:localized_template_content_id>/',
      views.ManageLocalizedTemplateContent.as_view(), name='manage_localized_template_content'),
   path('<str:app_uid>/delete-templatecontent/<int:pk>/', views.DeleteTemplateContent.as_view(),
      name='delete_template_content'),
   # translating
   path('<str:app_uid>/translate-template-content/<int:template_content_id>/<str:language>/',
      views.TranslateTemplateContent.as_view(), name='translate_template_content'),
   # images
   path('manage-template-content-image/<int:content_image_id>/', views.ManageTemplateContentImage.as_view(),
      name='manage_template_content_image'),
   path('manage-template-content-image/<int:content_type_id>/<int:object_id>/<str:image_type>/',
      views.ManageTemplateContentImage.as_view(), name='manage_template_content_image'),
   path('delete-template-content-image/<int:pk>/', views.DeleteTemplateContentImage.as_view(),
      name='delete_template_content_image'),
   path('get-template-content-formfields/<int:localized_template_content_id>/<str:content_key>/',
      views.GetTemplateContentFormFields.as_view(), name='get_template_content_form_fields'),
   # publishing and unpublishing template content
   path('<str:app_uid>/publish-template-content/<int:template_content_id>/', views.PublishTemplateContent.as_view(),
      name='publish_template_content'),
   path('<str:app_uid>/unpublish-template-content/<int:template_content_id>/', views.UnpublishTemplateContent.as_view(),
      name='unpublish_template_content'),
   # navigations
   path('<str:app_uid>/create-template-content-navigation/', views.ManageNavigation.as_view(),
      name='create_template_content_navigation'),
   path('<str:app_uid>/manage-template-content-navigation/<int:pk>/', views.ManageNavigation.as_view(),
      name='manage_template_content_navigation'),
   path('<str:app_uid>/publish-template-content-navigation/<int:navigation_id>/', views.PublishNavigation.as_view(),
      name='publish_template_content_navigation'),
   path('delete-template-content-navigation/<int:pk>/', views.DeleteNavigation.as_view(),
      name='delete_template_content_navigation'),
   path('<str:app_uid>/manage-template-content-navigation-entries/<int:pk>/', views.ManageNavigationEntries.as_view(),
      name='manage_template_content_navigation_entries'),
   path('<str:app_uid>/get-template-content-navigation-entries/<int:pk>/', views.GetNavigationEntriesTree.as_view(),
      name='get_template_content_navigation_entries'),
   path('<str:app_uid>/manage-template-content-navigation-entry/<int:navigation_id>/',
      views.ManageNavigationEntry.as_view(), name='create_template_content_navigation_entry'),
   path('<str:app_uid>/manage-template-content-navigation-entry/<int:navigation_id>/<int:pk>/',
      views.ManageNavigationEntry.as_view(), name='manage_template_content_navigation_entry'),
   path('delete-template-content-navigation-entry/<int:pk>/', views.DeleteNavigationEntry.as_view(),
      name='delete_template_content_navigation_entry'),
   # components
   path('<str:app_uid>/manage-component/<int:localized_template_content_id>/<str:content_key>/',
      views.ManageComponent.as_view(), name='manage_component'),
   path('<str:app_uid>/manage-component/<int:localized_template_content_id>/<str:content_key>/<uuid:component_uuid>/',
      views.ManageComponent.as_view(), name='manage_component'),
   path('<str:app_uid>/delete-component/<int:localized_template_content_id>/<str:content_key>/<uuid:component_uuid>/',
      views.DeleteComponent.as_view(), name='delete_component'),
   # component images
   path('manage-component-image/<int:content_image_id>/', views.ManageComponentImage.as_view(),
      name='manage_component_image'),
   path('manage-component-image/<int:content_type_id>/<int:object_id>/<str:image_type>/',
      views.ManageComponentImage.as_view(), name='manage_component_image'),
   path('delete-component-image/<int:pk>/', views.DeleteComponentImage.as_view(),
      name='delete_component_image'),
]
