from localcosmos_server.models import TaxonomicRestriction
from django.contrib.contenttypes.models import ContentType


'''
    - deliver context for rendering taxonomic restriction form
    - provide a method to store a restriction in the db
'''
class TaxonomicRestrictionMixin:
    

    def save_taxonomic_restriction(self, content_instance, form):

        lazy_taxon = form.cleaned_data.get('taxon', None)
        if lazy_taxon:
            restriction_type = form.cleaned_data['restriction_type']

            content_type = ContentType.objects.get_for_model(content_instance)

            restriction = TaxonomicRestriction(
                content_type = content_type,
                object_id = content_instance.id,
            )

            if restriction_type:
                restriction.restriction_type = restriction_type

            restriction.set_taxon(lazy_taxon)

            restriction.save()

        

        
