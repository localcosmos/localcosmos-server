from django.views.generic import TemplateView, FormView
from localcosmos_server.view_mixins import AppMixin
from localcosmos_server.generic_views import AjaxDeleteView
from django.urls import reverse
from django.shortcuts import get_object_or_404

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

from django.utils.decorators import method_decorator
from localcosmos_server.decorators import ajax_required

from .models import GeographyPolygon, PolygonCategory
from .forms import PolygonCategoryForm, PolygonForm

from localcosmos_server.models import App

import json


class GeographyOverview(AppMixin, TemplateView):
    template_name = 'geography/overview.html'
    

class GetPolygonCategories(AppMixin, TemplateView):
    template_name = 'geography/ajax/polygon_category_list.html'

    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = PolygonCategory.objects.filter(app=self.app).order_by('name', 'pk')
        return context


class GetCategoryPolygons(AppMixin, TemplateView):
    template_name = 'geography/ajax/polygon_list.html'

    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_id = self.kwargs['category_id']
        context['category'] = get_object_or_404(PolygonCategory, app=self.app, id=category_id)
        return context


class ManagePolygonCategory(AppMixin, FormView):
    template_name = 'geography/ajax/manage_polygon_category.html'
    form_class = PolygonCategoryForm
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        self.set_category(**kwargs)
        return super().dispatch(*args, **kwargs)
    
    def set_category(self, **kwargs):
        app = App.objects.get(uid=kwargs['app_uid'])
        category_id = self.kwargs.get('category_id')
        self.category = None
        if category_id:
            self.category = PolygonCategory.objects.get(app=app, id=category_id)
            
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.category is not None:
            kwargs['instance'] = self.category
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        action_url = reverse('geography:add_polygon_category', kwargs={'app_uid': self.app.uid})
        if self.category:
            action_url = reverse('geography:edit_polygon_category', kwargs={'app_uid': self.app.uid, 'category_id': self.category.id})
        context['action_url'] = action_url
        context['category'] = self.category
        context['success'] = False
        return context
    
    def form_valid(self, form):
        category = form.save(commit=False)
        category.app = self.app
        category.save()
        context = self.get_context_data()
        context['success'] = True
        return self.render_to_response(context)
    
    
class DeletePolygonCategory(AppMixin, AjaxDeleteView):
    model = PolygonCategory
    
    
class ManagePolygon(AppMixin, FormView):
    template_name = 'geography/ajax/manage_polygon.html'
    form_class = PolygonForm
    
    @method_decorator(ajax_required)
    def dispatch(self, *args, **kwargs):
        self.set_polygon(**kwargs)
        return super().dispatch(*args, **kwargs)
    
    def set_polygon(self, **kwargs):
        app = App.objects.get(uid=kwargs['app_uid'])
        category_id = self.kwargs['category_id']
        self.category = PolygonCategory.objects.get(app=app, id=category_id)
        polygon_id = self.kwargs.get('polygon_id')
        self.geography_polygon = None
        self.geojson_geometry_4326 = None
        if polygon_id:
            self.geography_polygon = GeographyPolygon.objects.get(app=app, id=polygon_id, category__id=category_id)
            self.geojson_geometry_4326 = self.geometry_to_geojson()
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['geography_polygon'] = self.geography_polygon
        context['geojson_geometry_4326'] = self.geojson_geometry_4326
        return context
    
    
    def get_initial(self):
        initial = super().get_initial()
        
        if self.geography_polygon:
            initial['name'] = self.geography_polygon.name
            initial['code'] = self.geography_polygon.code

        if self.geojson_geometry_4326:
            initial['polygon'] = json.dumps(self.geojson_geometry_4326)

        return initial
    
    
    def geometry_to_geojson(self):
        

        geojson = {
            "type":"FeatureCollection",
            "features": [
                #{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[5.097656,48.004625],[5.097656,50.541363],[10.83252,50.541363],[10.83252,48.004625],[5.097656,48.004625]]]}},
            ]
        }

        for geometry in self.geography_polygon.geometry:
            
            geometry_for_editor = geometry.clone()

            # We send/receive EPSG:4326 coordinates to the template.
            # Stored geometries are EPSG:3857, so convert before serializing
            # to avoid invalid SRID transforms on edit-save roundtrips.
            if geometry_for_editor.srid and geometry_for_editor.srid != 4326:
                geometry_for_editor.transform(4326)

            #map_sr = SpatialReference(4326)
            #db_sr = SpatialReference(3857)
            #trans = CoordTransform(db_sr, map_sr)

            #geometry.transform(trans)

            feature = {
                "type":"Feature",
                "properties":{},
                "geometry": json.loads(geometry_for_editor.geojson),
            }

            geojson['features'].append(feature)

        return geojson
    
    
   
    def form_valid(self, form):
        geojson_str = form.cleaned_data['polygon']
        
        name = form.cleaned_data['name']
        code = form.cleaned_data['code']
        if self.geography_polygon is None:
            self.geography_polygon = GeographyPolygon()
        
        
        geojson = json.loads(geojson_str)
        
        polygons = []

        for feature in geojson['features']:
            # 4326 is returned by the map service
            # GEOS will auto-translate it into 3857
            polygon = GEOSGeometry(json.dumps(feature['geometry']), srid=4326)
            polygons.append(polygon)
            
        multipoly = MultiPolygon(tuple(polygons), srid=4326)
            
        self.geography_polygon.name = name
        self.geography_polygon.code = code
        self.geography_polygon.geometry = multipoly
        self.geography_polygon.app = self.app
        self.geography_polygon.category = self.category
        self.geography_polygon.save()

        # Rebuild geometry payload for the response from the just-saved object.
        # Without this, repeated saves can render stale geometry from pre-save context.
        self.geojson_geometry_4326 = self.geometry_to_geojson()
        
        context = self.get_context_data()
        context['success'] = True
        return self.render_to_response(context)
            

class DeletePolygon(AppMixin, AjaxDeleteView):
    model = GeographyPolygon