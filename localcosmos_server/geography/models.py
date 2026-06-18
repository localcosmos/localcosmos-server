from django.contrib.gis.db import models

from localcosmos_server.models import App


class PolygonCategory(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='polygon_categories')
    name = models.CharField(max_length=255)
    
    @property
    def polygons(self):
        return GeographyPolygon.objects.filter(category=self).order_by('name', 'pk')

    def __str__(self):
        return self.name or str(self.pk)


class GeographyPolygon(models.Model):
    
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='geography_polygons')
    category = models.ForeignKey(PolygonCategory, on_delete=models.CASCADE, related_name='geography_polygons')
    
    geometry = models.GeometryField(srid=3857)
    name = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    

    def __str__(self):
        name = self.name or self.code or str(self.pk)
        return f'{name} ({self.category.name})'