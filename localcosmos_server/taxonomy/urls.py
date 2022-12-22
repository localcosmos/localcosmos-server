from django.urls import path, re_path
from . import views

urlpatterns = [
    path('<str:app_uid>/search-taxon/', views.SearchAppTaxon.as_view(), name='search_app_taxon'),
    path('<str:app_uid>/manage-taxonomic-restrictions/<int:content_type_id>/<int:object_id>/',
         views.ManageTaxonomicRestrictions.as_view(), name='manage_app_taxonomic_restrictions'),
     path('<str:app_uid>/manage-modeal-taxonomic-restrictions/<int:content_type_id>/<int:object_id>/',
         views.ManageModalTaxonomicRestrictions.as_view(), name='manage_modal_app_taxonomic_restrictions'),
    path('<str:app_uid>/remove-taxonomic-restriction/<int:pk>/',
         views.RemoveAppTaxonomicRestriction.as_view(), name='remove_app_taxonomic_restriction'),
]

