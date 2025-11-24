from django.contrib.auth import get_user_model
from accounts.models import Estudiante,Docente
from django.http import HttpResponseBadRequest, HttpResponseForbidden


User = get_user_model()

def get_user_type(user):
    if not user.is_authenticated:
        return None,None
    
    try:
        return 'estudiante', user.estudiante
    except Estudiante.DoesNotExist:
        pass
    try:
        return 'docente', user.docente
    except Estudiante.DoesNotExist:
        pass
    
    return 'generic', None

def require_estudiante(view_func):
    #  Decorator para vistar que requieren ser estudiante
    def wrapper(request, *args, **kwargs):
        user_type, profile = get_user_type(request.user)
        if user_type != 'estudiante':
            return HttpResponseForbidden("Acceso denegado. Solo para estudiantes")
        return view_func(request, *args,**kwargs)
    return wrapper

def require_docente(view_func):
    #  Decorator para vistar que requieren ser estudiante
    def wrapper(request, *args, **kwargs):
        user_type, profile = get_user_type(request.user)
        if user_type != 'docente':
            return HttpResponseForbidden("Acceso denegado. Solo para docentes")
        return view_func(request, *args,**kwargs)
    return wrapper