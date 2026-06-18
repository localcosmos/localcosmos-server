from django.urls import path

from . import views

app_name = 'geography'

urlpatterns = [
    path('<str:app_uid>/geographies/', views.GeographyOverview.as_view(),
         name='geography_overview'),
    path('<str:app_uid>/geographies/polygon-categories/', views.GetPolygonCategories.as_view(),
         name='get_polygon_categories'),
    path('<str:app_uid>/geographies/polygon-categories/<int:category_id>/polygons/', views.GetCategoryPolygons.as_view(),
         name='get_category_polygons'),
    path('<str:app_uid>/geographies/polygon-categories/add/', views.ManagePolygonCategory.as_view(),
         name='add_polygon_category'),
    path('<str:app_uid>/geographies/polygon-categories/<int:category_id>/', views.ManagePolygonCategory.as_view(),
         name='edit_polygon_category'),
    path('<str:app_uid>/geographies/polygon-categories/<int:pk>/delete/', views.DeletePolygonCategory.as_view(),
         name='delete_polygon_category'),
    path('<str:app_uid>/geographies/polygon-categories/<int:category_id>/polygons/add/', views.ManagePolygon.as_view(),
         name='add_polygon'),
    path('<str:app_uid>/geographies/polygon-categories/<int:category_id>/polygons/<int:polygon_id>/', views.ManagePolygon.as_view(),
         name='edit_polygon'),
    path('<str:app_uid>/geographies/polygon-categories/<int:category_id>/polygons/<int:polygon_id>/delete/', views.DeletePolygon.as_view(),
         name='delete_polygon'),
]