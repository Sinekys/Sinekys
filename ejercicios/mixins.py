from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.models import Diagnostico, Estudiante
from .models import Ejercicio,Intento,IntentoPaso
from accounts.services import diagnostico_finalizado
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest 

from typing import Tuple, Optional, Dict, Any
import logging


# get y validaciones
def get_estudiante_from_request(request) -> Tuple[Optional[Estudiante], Optional[JsonResponse]]:
    # Devuelve (estudiante,error_response) este ultimo es None si todo está bien
    try:
        estudiante = request.user.estudiante
        return estudiante,None
    except Exception:
        return None, HttpResponseBadRequest("Usuario no encontrado")
    

def obtener_o_validar_diagnostico(estudiante) -> Diagnostico:
    # logica de services.py
    from accounts.services import obtener_o_validar_diagnostico #Import local, pa evitar ciclos
    return obtener_o_validar_diagnostico(estudiante)

def diagnostico_activo_para_api(estudiante):
    from accounts.services import diagnostico_activo
    return diagnostico_activo(estudiante)

# Preparas sig ejercicio (html/json)
def prepare_next_payload(estudiante, wants_json:bool = False) -> Tuple[Optional[Dict[str,Any]], Optional[JsonResponse]]:
    # validar diagnostico
    # seleccionar sig ejercicio
    # generar contexto
    from .requestdiagnostico import contextualize_exercise_diagnostico
    from ejercicios.services import seleccionar_siguiente_ejercicio
    # from ..request import contextualize_exercise #Para ejercicio solo, conexto acorde a la carrera
     
     
    if wants_json:
        diag = diagnostico_activo_para_api(estudiante)
        if not diag:
            return None, JsonResponse({"error":"El diagnostico ya finalizó o expiró", "finalizado":True},status=403)
        diagnostico = diag
    else:
        diagnostico = obtener_o_validar_diagnostico(estudiante)
        if diagnostico.finalizado or diagnostico.is_expired():
            # devolver payload
            return {
                "finalizado": True,
                "diagnostico": diagnostico,
                "motivo": "Tiempo agotado" if diagnostico.is_expired() else "Precisión alcanzada"
            }, None
    
    ejercicio = seleccionar_siguiente_ejercicio(estudiante)
    if not ejercicio:
        diagnostico.finalizado = True
        diagnostico.save(update_fields=['finalizado'])
        return None, JsonResponse({"error": "No hay más ejercicios disponibles", "finalizado": True}, status=200)

    remaining_seconds = max(0, int(diagnostico.tiempo_restante()))
    contexto = contextualize_exercise_diagnostico(ejercicio)
    
    payload = {
        "estudiante": estudiante,
        "diagnostico": diagnostico,
        "ejercicio": ejercicio,
        "contexto": contexto,
        "remaining_seconds": remaining_seconds       
    }
    return payload, None

def crear_intento_servidor(estudiante, ejercicio,respuesta_estudiante:str, es_correcto: bool, pasos: list, diagnostico: Diagnostico):
    # Crear intento e intento paso usando el tiempo calculado por el servidor
    # devuelve el intento creado
    
    server_remaining = diagnostico.tiempo_restante()
    server_remaining_clamped = max(0.0, float(server_remaining))
    tiempo_usado_server = float(diagnostico.duracion_segundos) - server_remaining_clamped
    
    if tiempo_usado_server < 0: 
        tiempo_usado_server = 0.0

    intento = Intento.objects.create(
        estudiante=estudiante,
        ejercicio=ejercicio,
        respuesta_estudiante=respuesta_estudiante,
        es_correcto=es_correcto,
        puntos=1.0 if es_correcto else 0.0,
        tiempo_en_segundos=tiempo_usado_server,
        fecha_intento=timezone.now()
    )
    
    for orden, paso_texto in enumerate(pasos or [], start=1):
        IntentoPaso.objects.create(
            intento=intento,
            orden=orden,
            contenido=paso_texto,
            datos_aux={}
        )
    return intento

# Helpers de respuesta
# Helpers de respuesta
# Helpers de respuesta
def render_diagnostico_template(request,ejercicio,contexto,diagnostico,remaining_seconds):
    return render(request, "diagnostico/index.html",{
        "ejercicio": ejercicio,
        "contexto": contexto,
        "diagnostico": diagnostico,
        "remaining_seconds": remaining_seconds
    })

def json_net_excercise_response(ejercicio, contexto, theta=None, se=None, num_items=None):
    return JsonResponse({
        "success": True,
        "final": False,
        "theta": theta,
        "error": se,
        "num_items": num_items,
        "ejercicio": {
            "id": ejercicio.id,
            "enunciado": ejercicio.enunciado,
            "dificultad": float(ejercicio.dificultad),
        },
        "contexto": contexto 
    })


class DiagnosticoCompletadoMixin:
    # Bloquea el acceso si el diagnostico no está completado
    # Solo aplica a estudiantes
    # 
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Solo a estudiantes
        if not hasattr(request.user, 'estudiante'):
            return super().dispatch(request, *args, **kwargs)
        if not diagnostico_finalizado(request.user.estudiante):
            messages.warning(
                request,
                "Debes completar la prueba de diagnóstico antes de acceder a ejercicios individuales o grupales."
            )
            return render(request, 'ejercicios/bloqueo_diagnostico.html')

        return super().dispatch(request, *args, **kwargs)