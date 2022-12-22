from localcosmos_server.models import TaxonomicRestriction
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.models import App

class AppMixin:

    def dispatch(self, request, *args, **kwargs):

        self.app = App.objects.get(uid=kwargs['app_uid'])
        
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app' : self.app,
        })
        return context

    
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

        

'''
    currently, set_taxon is only supported by app_kit.ManagecontentImageMixin
'''
from localcosmos_server.taxonomy.lazy import LazyAppTaxon
from content_licencing.view_mixins import LicencingFormViewMixin  
from localcosmos_server.models import ServerContentImage, ServerImageStore 
class ContentImageViewMixin(LicencingFormViewMixin):

    ContentImageClass = ServerContentImage
    ImageStoreClass = ServerImageStore
    LazyTaxonClass = LazyAppTaxon

    def set_content_image(self, *args, **kwargs):

        new = False
        self.content_image = None
        
        if 'content_image_id' in kwargs:
            self.content_image = self.ContentImageClass.objects.get(pk=kwargs['content_image_id'])
            self.object_content_type = self.content_image.content_type
            self.content_instance = self.content_image.content
            image_type = self.content_image.image_type
        else:
            new = bool(self.request.GET.get('new', False))
            self.object_content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
            ContentModelClass = self.object_content_type.model_class()
            self.content_instance = ContentModelClass.objects.get(pk=kwargs['object_id'])

            # respect the image type, if one was given
            image_type = kwargs.get('image_type','image')

            if new == True:
                self.content_image = None
            else:
                self.content_image = self.ContentImageClass.objects.filter(content_type=self.object_content_type,
                                            image_type=image_type, object_id=self.content_instance.id).first()

        # if there is no content_image, it has to be a new one
        if not self.content_image:
            new = True
            
        self.image_type = image_type
        self.new = new

    def tree_instance(self):
        if self.taxon == None:
            return None
        return self.models.TaxonTreeModel.objects.get(taxon_latname=self.taxon.taxon_latname,
                                                      taxon_author=self.taxon.taxon_author)
    

    def get_new_image_store(self):
        image_store = self.ImageStoreClass(
            uploaded_by = self.request.user,
        )

        return image_store

    def save_image(self, form):

        # flag if the user selected an existing image
        is_linked_image = False
        
        # save the uncropped image alongside the cropping parameters
        # the cropped image itself is generated on demand: contentImageInstance.image()

        # first, store the image in the imagestore
        if not self.content_image:

            # first, check if there is just a linked image
            referred_content_image_id = form.cleaned_data.get('referred_content_image_id', None)

            if referred_content_image_id:
                is_linked_image = True
                referred_content_image = self.ContentImageClass.objects.get(pk=referred_content_image_id)
                image_store = referred_content_image.image_store

            else:
                image_store = self.get_new_image_store()
        else:
            # check if the image has changed
            current_image_store = self.content_image.image_store

            if current_image_store.source_image != form.cleaned_data['source_image']:
                image_store = self.get_new_image_store()
            else:
                image_store = current_image_store


        if is_linked_image == False:
            
            if self.taxon:
                image_store.set_taxon(self.taxon)

            image_store.source_image = form.cleaned_data['source_image']
            image_store.md5 = form.cleaned_data['md5']

            image_store.save()

        # store the link between ImageStore and Content in ContentImage
        if not self.content_image:
            
            self.content_image = self.ContentImageClass(
                content_type = self.object_content_type,
                object_id = self.content_instance.id,
            )

        self.content_image.image_store = image_store

        # crop_parameters are optional in the db
        # this makes sense because SVGS might be uploaded
        self.content_image.crop_parameters = form.cleaned_data.get('crop_parameters', None)

        # features are optional in the db
        self.content_image.features = form.cleaned_data.get('features', None)

        image_type = form.cleaned_data.get('image_type', None)
        if image_type:
            self.content_image.image_type = image_type


        requires_translation = form.cleaned_data.get('requires_translation', False)
        self.content_image.requires_translation = requires_translation

        # there might be text
        if form.cleaned_data.get('text', None):
            self.content_image.text = form.cleaned_data['text']
        
        self.content_image.save()

        # register content licence
        if is_linked_image == False:
            self.register_content_licence(form, self.content_image.image_store, 'source_image')
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = self.object_content_type
        context['content_instance'] = self.content_instance
        context['image_type'] = self.image_type
        context['content_image'] = self.content_image
        context['content_image_taxon'] = self.taxon
        context['new'] = self.new

        return context
    

    def get_initial(self):
        initial = super().get_initial()

        if self.content_image:
            # file fields cannot have an initial value [official security feature of all browsers]
            initial['crop_parameters'] = self.content_image.crop_parameters
            initial['features'] = self.content_image.features
            initial['source_image'] = self.content_image.image_store.source_image
            initial['image_type'] = self.content_image.image_type
            initial['text'] = self.content_image.text
            initial['requires_translation'] = self.content_image.requires_translation

            licencing_initial = self.get_licencing_initial()
            initial.update(licencing_initial)

        else:
            initial['image_type'] = self.image_type
            
        initial['uploader'] = self.request.user

        return initial

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['content_instance'] = self.content_instance
        if self.content_image:
            form_kwargs['current_image'] = self.content_image.image_store.source_image
        return form_kwargs

    def set_taxon(self, request):
        self.taxon = None

