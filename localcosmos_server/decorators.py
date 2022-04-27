from django.http import HttpResponseBadRequest

from functools import wraps

def ajax_required(function):
    @wraps(function)
    def decorator(request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseBadRequest('Bad request')
        return function(request, *args, **kwargs)

    return decorator
