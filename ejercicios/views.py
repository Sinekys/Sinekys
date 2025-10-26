from django.views import View
from django.utils.decorators import method_decorator

from django.shortcuts import render,get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone
# from django.urls import reverse
import json
import re

# registro
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

# Models
from ejercicios.models import Ejercicio, Intento, IntentoPaso 
from accounts.models import Estudiante, Diagnostico

# services
    # here
from ejercicios.services import actualizar_diagnostico, seleccionar_siguiente_ejercicio
from accounts.services import obtener_o_validar_diagnostico, diagnostico_activo


# API ChatGPT
# from request import contextualize_exercise
from .requestdiagnostico import contextualize_exercise_diagnostico
# from ..request import contextualize_exercise

# logs
import logging
logger = logging.getLogger(__name__)

# Mixins creados
from .mixins import (
    get_estudiante_from_request,
    prepare_next_payload,
    crear_intento_servidor,
    render_diagnostico_template,
    json_net_excercise_response,    
    DiagnosticoCompletadoMixin

)


# Normalizar respuesta
#  2X === 2x
def normalizar_respuesta(respuesta: str) -> str:
    if respuesta is None:
        return ""
    r = respuesta.strip().lower() 
    
    # Eliminar espacios alrededor de operadores
    r = re.sub(r'\s*\+\s*', '+', r)
    r = re.sub(r'\s*-\s*', '-', r)
    r = re.sub(r'\s*=\s*', '=', r)
    r = re.sub(r'\s*\*\s*', '*', r)
    r = re.sub(r'\s*/\s*', '/', r)
    
    # Simplificar paréntesis: ( x + 1 ) → (x+1)
    r = re.sub(r'\(\s*', '(', r)
    r = re.sub(r'\s*\)', ')', r)
    
    # Unificar potencias: ^2, **2, al_cuadrado → ^2
    r = re.sub(r'\*\*2|\^2|\b(al\s*_*\s*cuadrado)\b', '^2', r)
    
    # Por último tengo que trabajar con los puntos y los decimales
    # lo que se puede volver un problema, que pasa si pone 
    # 17,5 esta puede ser la respuestas de algebra o de funciones siendo 17,5 un punto en una gráfica
    
    return r

    
def evaluar_respuesta(respuesta_estudiante: str, respuesta_correcta: str) -> tuple[bool, float]:
    es_correcto = normalizar_respuesta(respuesta_estudiante) == normalizar_respuesta(respuesta_correcta)

    puntos = 1.0 if es_correcto else 0.0
    return (es_correcto, puntos)

@method_decorator(login_required, name='dispatch')
class DiagnosticTestView(View):

    def get(self, request):
        # accept = request.headers.get('Accept','')
        wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        estudiante, err_resp = get_estudiante_from_request(request)
        if err_resp:
            return err_resp

        payload, err = prepare_next_payload(estudiante, wants_json=wants_json)
        if err:
            return err

        # payload puede indicar finalizado
        if payload.get("finalizado"):
            diag = payload["diagnostico"]
            return render(request, "diagnostico/finalizado.html",{
                "diagnostico": diag,
                "motivo": payload.get("motivo", "")
            })


        if wants_json:
            ejercicio = payload["ejercicio"]
            contexto = payload["contexto"]
            return JsonResponse({
                "ejercicio": {
                    "id": ejercicio.id,
                    "enunciado": ejercicio.enunciado,
                    "dificultad": float(ejercicio.dificultad)
                },
                "contexto": contexto
            })
        else:
            return render(request, "diagnostico/index.html", {
                "ejercicio": payload["ejercicio"],
                "contexto": payload["contexto"],
                "diagnostico": payload["diagnostico"],
                "remaining_seconds": payload["remaining_seconds"]
            })
            

    
    @transaction.atomic
    def post(self, request):
        # necesito obtener los pasos y la respuesta del estudiante
        if request.content_type != "application/json":
            return JsonResponse({"error": "Se esparaba json"}, 400)
        estudiante, err_resp = get_estudiante_from_request(request)
        
        if err_resp:
            return err_resp
        
        # validar diagnostico activo para API
        payload_check, err = prepare_next_payload(estudiante, wants_json=True)
        if err:
            return err #incluye caos finalizado
        
        
        diagnostico = payload_check["diagnostico"]
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error":"Json inválido"}, 400)
        
        ejercicio_id = data.get("ejercicio_id")
        respuesta_estudiante = (data.get("respuesta_estudiante") or "").strip()
        pasos = data.get("pasos",[])

        if not ejercicio_id:
            return JsonResponse({"error":"Falta id del ejercicio"}, status=400)
        
        ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
        es_correcto, puntos = evaluar_respuesta(respuesta_estudiante, ejercicio.solucion)
        # ojo, la variable puntos no se está utilizando
        client_remaining = None
        try:
            client_remaining = float(data.get("remaining_seconds")) if data.get("remaining_seconds") is not None else None
        except Exception:
            client_remaining = None
        
        server_remaining = diagnostico.tiempo_restante()
        server_remaining_clamped = max(0.0, float(server_remaining))
        if client_remaining is not None and abs(client_remaining - server_remaining_clamped) > 5:
            logger.warning(
                "Client-reported remaining (%s) differs from server (%s) for diagnostico %s / estudiante %s",
                client_remaining, server_remaining_clamped, diagnostico.id, estudiante.pk
            )
            
    #    comprobación extra por si expiró entre peticiones
        if diagnostico.is_expired():
            diagnostico.finalizado = True
            diagnostico.save(update_fields=["finalizado"])
            return JsonResponse({"success": True, "final":True,"motivo":"Tiempo agotado antes del envío"}, status=200)
        
        
        # Crwar intento
        intento = crear_intento_servidor(estudiante,ejercicio, respuesta_estudiante,es_correcto,pasos,diagnostico)
        # intento al parecer tampoco esta siendo utilizado
        
        # actualizar dianostico y obtener theta + SE
        theta_actual, se = actualizar_diagnostico(estudiante)
        
        # actualizar el objeto Diagnostico con los nuevos valores
        diagnostico.theta = theta_actual
        diagnostico.error_estimacion = se #esto debería venir desde services.py
        diagnostico.save(update_fields=["theta","error_estimacion"])
        
        # criterios de finalizacion
        # criterios de finalizacion
        # criterios de finalizacion
        num_items = Intento.objects.filter(estudiante=estudiante).count() #Ojo puede haber un problema, ya que si el es estudiante cancela la prueba, los intentos seguiran registrados y por lo tanto el número aumentaría
        max_items = 30
        umbral_se = 0.4
        
        finalizado = False
        motivo = ""
        if se < umbral_se:
            finalizado = True
            motivo = "Precisión alcanzada"
        elif num_items >= max_items:
            finalizado = True
            motivo = "Límite de ejercicios alcanzado"
        elif diagnostico.is_expired():
            finalizado = True
            motivo = "Tiempo agotado"

        if finalizado:
            diagnostico.finalizado = True
            diagnostico.save(update_fields=["finalizado"])
            return JsonResponse({
                "success": True,
                "final": True,
                "motivo": motivo,
                "theta": theta_actual,
                "error": se
            })
        
             
        siguiente_ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        
        
        if not siguiente_ejercicio:
            # Caso extremo: no hay más ejercicios
            diagnostico.finalizado = True
            diagnostico.save(update_fields=["finalizado"])
            return JsonResponse({
                "success": True,
                "final": True,
                "motivo": "No hay más ejercicios disponibles",
                "theta": theta_actual,
                "error": se
            })
            
        # contexto = contextualize_exercise_diagnostico(siguiente_ejercicio)
        try:
            from .requestdiagnostico import contextualize_exercise_diagnostico
            contexto = contextualize_exercise_diagnostico(siguiente_ejercicio)
        except Exception:
            contexto = {
                "display_text": siguiente_ejercicio.enunciado,
                "hint": "hint"
            }
            
        return json_net_excercise_response(siguiente_ejercicio,contexto,theta=theta_actual,se=se,num_items=num_items)
        
        
        # Cómo determino el umbral del error estándar?
        # por qué 0.4???
        # No lo puedo suponer
        
# Tengo pensado en refactorizar  
class EjercicioView(DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    def get(self, request):
        
        return render(request, 'ejercicios/ejercicio.html')
    
    def post(self, request):
        
        pass
    
    
class MatchMakingGroupView(DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    def get(self,request):
        
        return render(request,'ejercicios/matchmaking_group.html')
    
    
    def post(self,request):
        
        pass
    
# No sé si voy a necesitar esta clase la verdad...
# class ContinuarEjercicioGrupal(MatchMakingGroupView,DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    
    
    
    