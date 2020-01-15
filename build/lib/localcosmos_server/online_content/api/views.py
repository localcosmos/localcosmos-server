from rest_framework.views import APIView
from django.core.exceptions import PermissionDenied
from rest_framework.renderers import TemplateHTMLRenderer, BrowsableAPIRenderer
from rest_framework.exceptions import ParseError, NotFound

from localcosmos_server.online_content.models import (TemplateContent, LocalizedTemplateContent,
                                                      TemplateContentFlags, SlugTrail)

from localcosmos_server.models import App

from django.template import Context
from django.http import HttpResponse, Http404


'''
    ONLINE CONTENT
    - fetch online content html and previews
    - always returns html
    - no authentication required
'''
'''
    GetOnlineContent
    - fetch TemplateContent by [localized?]slug
'''
class GetOnlineContent(APIView):

    permission_classes = ()
    
    # the app has to set the ACCEPT header to html only
    # BrowsableAPIRenderer is for testing purposes only
    renderer_classes = (TemplateHTMLRenderer, BrowsableAPIRenderer)
    template_name = None # set during get

    def get_object(self):
        # localized template content is fetched by localized_slug
        
        slug = self.request.query_params.get('slug', None)
        preview_token = self.request.query_params.get('preview_token', None)
        
        if not slug:
            raise ParseError('GET param slug is missing')
        
        localized_template_content = LocalizedTemplateContent.objects.filter(slug=slug).first()

        # maybe it is an old slug
        if not localized_template_content:
            slug_trail = SlugTrail.objects.filter(old_slug=slug)

            while slug_trail and not localized_template_content:
                if slug_trail.count() != 1:
                    break

                new_slug = slug_trail.first().new_slug
                localized_template_content = LocalizedTemplateContent.objects.filter(slug=new_slug).first()

                if not localized_template_content:
                    slug_trail = SlugTrail.objects.filter(old_slug=new_slug)
                

        if not localized_template_content:
            raise Http404('TemplateContent not found')
        
        if preview_token is None:
            # return the published version
            if not localized_template_content or not localized_template_content.published_version:
                raise Http404('TemplateContent not found')

        else:
            # preview qas requested, make security checks
            token_is_valid = localized_template_content.validate_preview_token(preview_token)

            # currently, this is disabled: nav entries (links) in the preview of the appbuilder should work
            if not token_is_valid == True:
                raise PermissionDenied('Invalid preview token')
                

        return localized_template_content
    

    def get_context_data(self, **kwargs):
        self.request.language = self.object.language
        context = {
            'user': self.request.user,
            'request' : self.request,
            'template_content' : self.object.template_content,
            'localized_template_content' : self.object,
            'app' : self.object.template_content.app,
            'preview' : False,
        }

        if 'preview_token' in self.request.query_params:
            context['preview'] = True

        # set the base_template
        # context["base_template"] = "base.html"
        
        # sections may use different base templates
        if "section" in kwargs:
            section = kwargs["section"]
            settings = request.cms.load_theme_settings()
            context["base_template"] = settings["sections"][section]["extends"]
        
        return context


    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # get the template
        template = self.object.get_template()
        context = self.get_context_data(**kwargs)
        c = Context(context)
        rendered = template.render(c)

        return HttpResponse(rendered)


'''
    GetOnlineContentByFlag
    - get e.g. navigation entries by TemplateContentFlag
    - as multiple apps are possible per user, app-dependant retrieval is necessary
'''
class GetOnlineContentList(APIView):
    permission_classes = ()
    renderer_classes = (TemplateHTMLRenderer,)
    template_name = None # set during get


    def get(self, request, *args, **kwargs):
        
        flag = self.request.query_params.get('flag', None)
        app_uuid = self.request.query_params.get('app_uuid', None)

        app_state = 'published'

        if flag and app_uuid:
            
            app = App.objects.filter(uuid=app_uuid).first()

            if app:
                language = self.request.query_params.get('language', app.primary_language)
                
                if 'preview' in self.request.query_params:
                    app_state = 'preview'

                flag_tree = TemplateContentFlags.objects.get_tree(app, flag, language, app_state=app_state)

                # read the template_name from theme settings
                theme_settings = app.get_online_content_settings()
                template_name = theme_settings['flags'][flag]['template_name']

                template = app.get_online_content_template(template_name)

                context = {
                    'app' : app,
                    'flag_tree' : flag_tree,
                }

                c = Context(context)
                rendered = template.render(c)
        
                return HttpResponse(rendered)
        
        raise Http404('No Online Content found')   
