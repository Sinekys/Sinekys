from django.utils import timezone
from .models import Diagnostico


def obtener_o_validar_diagnostico(estudiante):
    # Devuelve el diagnostico del estudiante
    # si no existe lo crea
    # si ya terminó, lo marca
    
    diagnostico, created = Diagnostico.objects.get_or_create(
        estudiante=estudiante,
        defaults={
            'theta': 0.0,
            'error_estimacion': 1.0,
            'finalizado': False,
            'fecha_inicio': timezone.now()
        }
    )
    if  not created and diagnostico.fecha_inicio is None and not diagnostico.finalizado:
        diagnostico.fecha_inicio = timezone.now()
        diagnostico.save(update_fields=['fecha_inicio'])
    
    return diagnostico

def diagnostico_finalizado(estudiante):
    return Diagnostico.objects.filter(
        estudiante=estudiante,
        finalizado=True
    ).exists()

def diagnostico_activo(estudiante):
    # Devuelve si el diagnostico está activo (ni finalizado ni expirado)
    # Si ya finalizó, None
    
    try:
        diag = Diagnostico.objects.get(estudiante=estudiante)
        if diag.finalizado or diag.is_expired():
            return None
        return diag
    except Diagnostico.DoesNotExist:
        return None