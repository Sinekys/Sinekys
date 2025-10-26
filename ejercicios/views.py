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
# Mixins creados
from .mixins import DiagnosticoCompletadoMixin



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
    
    def _prepare_next(self,request,wants_json: bool = False):
        # Logica comun entre respuestas html y json:
        # get: Estudiante, Diagnostico, Siguiente Ejercicio y Contexto
        try:
            estudiante = request.user.estudiante
        except Estudiante.DoesNotExist:
            if wants_json:
                return(JsonResponse({"error":"Estudiante no encontrado"}, status=400), None)
            return (HttpResponseBadRequest('Usuario no encontrado'), None)
        
        # json or html
        if wants_json:
            diag_activo = diagnostico_activo(estudiante)
            if not diag_activo:
                return(JsonResponse({
                    "error": "El diagnostico ya finalizó o expiró",
                    "finalizado": True,
                }, status=403), None)
            
            diagnostico = diag_activo
        else: 
            diagnostico = obtener_o_validar_diagnostico(estudiante)
            if diagnostico.finalizado or diagnostico.is_expired():
                motivo = 'Tiempo agotado' if diagnostico.is_expired() else 'Precisión alcanzada'
                return (render(request, "diagnostico/finalizado.html",{
                    'diagnostico': diagnostico,
                    'motivo': motivo
                }), None)
                
        ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        if not ejercicio:
            diagnostico.finalizado = True
            diagnostico.save(update_field=['finalizado'])
            if wants_json:
                return (JsonResponse({
                    "error": "No hay ejercicios disponibles",
                    "finalizado": True,
                },status=200), None)
            return (render(request, "diagnostico/finalizado.html",{
                'diagnostico': diagnostico,
                'motivo': 'no hay más ejercicios disponibles'
            }), None)
        remaining_seconds = max(0, int(diagnostico.tiempo_restante()))
        contexto = contextualize_exercise_diagnostico(ejercicio)

        payload = {
            "estudiante": estudiante,
            "diagnostico": diagnostico,
            "ejercicio": ejercicio,
            "contexto": contexto,
            "remaining_seconds": remaining_seconds
        }
        return (None, payload)


    def get(self, request):
        accept = request.headers.get('Accept','')
        wants_json = 'application/json' in accept or request.herads.get('X-Requested-With') == 'XMLHttpRequest'
        err, payload = self._prepare_next(request, wants_json=wants_json)
        if err:
            return err
        
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
        
    def _get_html_response(self, request):

        diagnostico = obtener_o_validar_diagnostico(estudiante)
        
        if diagnostico.finalizado or diagnostico.is_expired():
            # redirigir al inicio
            return render(request, "diagnostico/finalizado.html", {
                'diagnostico': diagnostico,
                'motivo': 'Tiempo agotado' if diagnostico.is_expired() else 'Precisión alcanzada'
            })
            
            #get ejercicio 
        ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        # logging.getLogger(__name__).info(f"Diagnóstico ID: {diagnostico.id}, fecha_inicio: {diagnostico.fecha_inicio}")

        if not ejercicio:
            diagnostico.finalizado = True
            diagnostico.save(update_fields=['finalizado'])
            return render(request, "diagnostico/finalizado.html",{
                'diagnostico': diagnostico,
                'motivo': 'no hay más ejercicios'
            })
            
            
            
        remaining_seconds = max(0,int(diagnostico.tiempo_restante()))
        contexto = contextualize_exercise_diagnostico(ejercicio)
        context = {
            "ejercicio": ejercicio,
            "contexto": contexto,
            "diagnostico": diagnostico,
            "remaining_seconds": remaining_seconds
        }
        return render(request, "diagnostico/index.html", context)
    
    
    def _get_json_response(self, request):
        try:
            estudiante = request.user.estudiante
            
        except Estudiante.DoesNotExist:
            return HttpResponseBadRequest('Usuario no encontrado x_x')
        
    
        diagnostico_activo = diagnostico_activo(estudiante)
        if not diagnostico_activo:
            return JsonResponse({
                "error": "El diagnóstico ya finalizó o expiró",
                "finalizado": True
            }, status=403)
        
        
        ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        
        if not ejercicio:
            diag = Diagnostico.objects.get(estudiante=estudiante)
            diag.finalizado = True
            diag.save(update_fields=['finalizado'])
            return JsonResponse({"error":"No hay ejercicios disponibles",
                                "finalizado": True,
                                },status=200)
    
    
        contexto = contextualize_exercise_diagnostico(ejercicio)
        return JsonResponse({
                    "ejercicio": {
                    "id":ejercicio.id,
                    "enunciado": ejercicio.enunciado,
                    "dificultad": float(ejercicio.dificultad)
                },
                "contexto":contexto
                })
    
    

    
    @transaction.atomic
    def post(self, request):
        # necesito obtener los pasos y la respuesta del estudiante
        if request.content_type != "application/json":
            return JsonResponse({"error": "Se esparaba json"}, 400)
        
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error":"Json inválido"}, 400)
        # get estudiante
        try:
            estudiante = request.user.estudiante
        except Estudiante.DoesNotExist:
            return JsonResponse({"error":"Estudiante no encontrado"}, 400)
        
        diagnostico_activo = diagnostico_activo(estudiante) 
        

        if not diagnostico_activo:
            return JsonResponse({
            "success": True,
            "final": True,
            "motivo": "Diagnostico ya finalizado o tiempo agotado",
            "mensaje":"Respuesta registrada correctamente"
        })
        diagnostico = diagnostico_activo #ya está activo
        
        # payload para los ejercicios
        ejercicio_id = payload.get("ejercicio_id")
        respuesta_estudiante = payload.get("respuesta_estudiante", "").strip()
        pasos = payload.get("pasos", []) #lista de strings
        
        
        if not ejercicio_id:
            return JsonResponse({"error":"Falta id del ejercicio"}, status=400)
        
        ejercicio = get_object_or_404(Ejercicio, pk = ejercicio_id)
        
        # evaluar
        es_correcto, puntos = evaluar_respuesta(respuesta_estudiante, ejercicio.solucion)
       
        server_remaining = diagnostico.tiempo_restante() #float en seg
        server_remaining_clamped = max(0.0, float(server_remaining))
            
        tiempo_usado_server = float(diagnostico.duracion_segundos) - server_remaining_clamped
            
        if tiempo_usado_server <0:
            tiempo_usado_server = 0.0
        client_remaining = None
        try:
            client_remaining = float(payload.get("remaining_seconds")) if payload.get("remaining_seconds") else None
        except Exception:
            client_remaining = None
        

        if client_remaining is not None and abs(client_remaining - server_remaining_clamped) > 5:
        # diferencia mayor a 5s -> loggear (no bloquear)
            logging.getLogger(__name__).warning(
                "Client-reported remaining (%s) differs from server (%s) for diagnostico %s / estudiante %s",
                client_remaining, server_remaining_clamped, diagnostico.id, estudiante.pk
            )
       
    #    comprobación extra por si expiró entre peticiones
        if diagnostico.is_expired():
            diagnostico.finalizado = True
            diagnostico.save(update_fields=["finalizado"])
            return JsonResponse({"success": True, "final":True,"motivo":"Tiempo agotado antes del envío"}, status=200)
        
        
        # Crwar intento
        intento = Intento.objects.create(
            estudiante=estudiante,
            ejercicio=ejercicio,
            respuesta_estudiante=respuesta_estudiante,
            es_correcto=es_correcto,
            puntos=puntos,
            tiempo_en_segundos=tiempo_usado_server,
            fecha_intento=timezone.now()
        )
        
        # guardar pasos
        for orden, paso_texto in enumerate(pasos, start=1):
            IntentoPaso.objects.create(
                intento=intento,
                orden=orden,
                contenido=paso_texto,
                datos_aux={} #futuro variables intermedias?
            )
            
        # actualizar dianostico y obtener theta + SE
        theta_actual, se = actualizar_diagnostico(estudiante)
        
        # actualizar el objeto Diagnostico con los nuevos valores
        diagnostico.theta = theta_actual
        diagnostico.error_estimacion = se #esto debería venir desde services.py
        diagnostico.save()
        
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
            diagnostico.save()
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
            diagnostico.save()
            return JsonResponse({
                "success": True,
                "final": True,
                "motivo": "No hay más ejercicios disponibles",
                "theta": theta_actual,
                "error": se
            })
            
        contexto = contextualize_exercise_diagnostico(siguiente_ejercicio)

        return JsonResponse({
            "success": True,
            "final": False,
            "theta": theta_actual,
            "error": se,
            "num_items": num_items,
            "ejercicio": {
                "id": siguiente_ejercicio.id,
                "enunciado": siguiente_ejercicio.enunciado,
                "dificultad": float(siguiente_ejercicio.dificultad)
            },
            "contexto": contexto
        })
        
        
        # Cómo determino el umbral del error estándar?
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
    
    
    
    