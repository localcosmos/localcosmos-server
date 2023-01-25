from django.http import HttpResponseBadRequest

from functools import wraps

def ajax_required(function):
    @wraps(function)
    def decorator(request, *args, **kwargs):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return HttpResponseBadRequest('Bad request')
        return function(request, *args, **kwargs)

    return decorator
