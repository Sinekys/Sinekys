from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import Diagnostico, Estudiante
from ejercicios.models import Intento

# Create your views here.

def home_view(request):
    
    if not request.user.is_authenticated:
        return render(request, 'index.html')
    # usuario loggeado
    
    diagnostico_completado = False
    if hasattr(request.user,'estudiante'):
        diagnostico_completado = Diagnostico.objects.filter(
            estudiante = request.user.estudiante,
            finalizado=True
        ).exists()
    #ultimos ejercicios estudiante
    # ultimos = Intento.objects.filter(estudiante=estudiante).select_related('ejercicio').order_by('-fecha_intento')[:10]
    
        
        
    # if hasattr(request.user,'docente'):
    #     estudiantes = Estudiante.objects.filter(
    #         docente = request.user.docente,
    #         
    #     ).exists()    
        
        
    context = {
        'diagnostico_completado': diagnostico_completado
    }        
    
    return render(request, 'main_page.html', context)


def about(request):
    return render(request, 'NoLogged/About.html')

def goals(request):
    return render(request, 'NoLogged/Goals.html')

def how_does_it_work(request):
    return render(request, 'NoLogged/HowDoesItWork.html')