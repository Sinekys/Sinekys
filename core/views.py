from django.shortcuts import render,redirect

# from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from accounts.models import Diagnostico
from ejercicios.models import Intento, Feedback, FeedbackPasos
from ejercicios.mixins import get_estudiante_from_request
from django.db.models import Prefetch
from .services import get_user_type
from core.models import Carrera, Materia

from django.conf import settings

import logging
logger = logging.getLogger(__name__)

# Create your views here.
@login_required
def home_view(request):
    user_type, profile = get_user_type(request.user)    
    if user_type == 'estudiante':
        from accounts.models import Diagnostico
        from ejercicios.models import Intento, Feedback
        from django.db.models import Prefetch
        from django.conf import settings
        
        # Obtener configuración
        max_items = getattr(settings, 'DIAGNOSTICO_MAX_EJERCICIOS', 30)
        
        # Determinar si el diagnóstico está completado
        diagnostico_completado = False
        diagnostico = None
        
        try:
            diagnostico = profile.diagnostico
            if diagnostico.finalizado:
                diagnostico_completado = True
        except Diagnostico.DoesNotExist:
            # No tiene diagnóstico, crear uno si es necesario
            if Intento.objects.filter(estudiante=profile).exists():
                from accounts.services import obtener_o_validar_diagnostico
                diagnostico = obtener_o_validar_diagnostico(profile)
        
        if not diagnostico_completado:
            # Verificar si tiene suficientes ejercicios para considerar completado
            num_intentos = Intento.objects.filter(estudiante=profile).count()
            min_ejercicios = max(10, int(max_items * 0.3))  # Al menos 10 o 30% del máximo
            
            if num_intentos >= min_ejercicios:
                diagnostico_completado = True
                if diagnostico and not diagnostico.finalizado:
                    diagnostico.finalizado = True
                    diagnostico.save()
        
        
        feedback_prefetch = Prefetch(
            'feedback_set',
            queryset=Feedback.objects.order_by('-fecha_feedback'),
            to_attr='feedbacks'
        )
        ultimos = Intento.objects.filter(
            estudiante=profile
        ).select_related(
            'ejercicio'
        ).prefetch_related(
            feedback_prefetch
        ).order_by(
            '-fecha_intento'
        )[:10]
        
        context = {
            'is_estudiante': True,
            'diagnostico_completado': diagnostico_completado,
            'ultimos': ultimos
        }
        return render(request, 'main_page.html', context)
    
    elif user_type == 'docente':
        # Obtener datos específicos para docentes
        context = {
            'is_docente': True,
            # ... datos específicos para docentes ...
        }
        return render(request, 'docente/main_page.html', context)
    
    else:
        # Usuario genérico (debería ser raro aquí por el @login_required)
        return redirect('index')
    
    
def index_view(request):
    """Vista para usuarios no autenticados"""
    if request.user.is_authenticated:
        return redirect('mainPage')
    return render(request, 'index.html')

    
def about(request):
    return render(request, 'NoLogged/About.html')

def goals(request):
    return render(request, 'NoLogged/Goals.html')

def how_does_it_work(request):
    return render(request, 'NoLogged/HowDoesItWork.html')

def pricing(request):
    return render(request, 'NoLogged/Pricing.html')

def terminos(request):
    return render(request, 'legal/Terminos.html')
def privacidad(request):
    return render(request, 'legal/Privacidad.html')      
def ayuda(request):
    return render(request, 'legal/Ayuda.html')

def ejercicio_grupal_view(request):
    # Lógica para el ejercicio grupal
    return render(request, 'future/ejercicio_grupal.html')

def dashboard(request):
    carreras = Carrera.objects.all()  # ← AQUÍ
    return render(request, 'dashboard/dashboard.html', {
        "carreras": carreras,
        "materias": Materia.objects.all()
    })