from django.urls import path

from . import views

app_name = 'achievements'

urlpatterns = [
    path('<str:app_uid>/achievements/', views.ListAchievements.as_view(), name='achievements_list'),
    path('<str:app_uid>/achievements/point_rules/', views.GetPointRues.as_view(), name='point_rules_list'),
    path('<str:app_uid>/achievements/point_rule/add/', views.ManagePointRule.as_view(), name='add_point_rule'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/edit/', views.ManagePointRule.as_view(), name='edit_point_rule'),
    path('<str:app_uid>/achievements/point_rule/<int:pk>/delete/', views.DeletePointRule.as_view(), name='delete_point_rule'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/dataset-condition/add/', views.ManageDatasetCondition.as_view(),
         name='add_dataset_condition'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/dataset-condition/<int:condition_id>/edit/', views.ManageDatasetCondition.as_view(),
         name='edit_dataset_condition'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/geography-condition/add/', views.ManageGeographyCondition.as_view(),
         name='add_geography_condition'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/geography-condition/<int:condition_id>/edit/', views.ManageGeographyCondition.as_view(),
         name='edit_geography_condition'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/taxon-condition/add/', views.ManageTaxonCondition.as_view(),
         name='add_taxon_condition'),
    path('<str:app_uid>/achievements/point_rule/<int:rule_id>/taxon-condition/<int:condition_id>/edit/', views.ManageTaxonCondition.as_view(),
         name='edit_taxon_condition'),
    path('<str:app_uid>/achievements/point_rule/condition/<int:pk>/delete/', views.DeletePointRuleCondition.as_view(),
         name='delete_point_rule_condition'),
]
