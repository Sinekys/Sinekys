from django.views import View
from django.utils.decorators import method_decorator

from django.shortcuts import render,get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

import json
import re

from django.contrib import messages
# registro
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

# Models
from ejercicios.models import Ejercicio, Intento, IntentoPaso,PasoEjercicio,Feedback,FeedbackPasos,TipoFeedback
from accounts.models import Estudiante, Diagnostico

# services
from ejercicios.services import actualizar_diagnostico, seleccionar_siguiente_ejercicio
# logs
import logging
logger = logging.getLogger(__name__)

# Mixins creados
from .mixins import (
    get_estudiante_from_request,
    prepare_next_payload_diagnostico,
    prepare_next_payload_normal,
    crear_intento_servidor,
    # render_diagnostico_template,
    json_next_excercise_response,    
    DiagnosticoCompletadoMixin,
    select_mode,
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
        post_url = reverse('diagnostico')
        wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        estudiante, err_resp = get_estudiante_from_request(request)
        if err_resp:
            return err_resp

        payload, err = prepare_next_payload_diagnostico(estudiante, wants_json=wants_json)
        if err:
            return err

        # payload puede indicar finalizado
        if payload.get("finalizado"):
            return render(request, "diagnostico/finalizado.html",payload)

        if wants_json:
            return JsonResponse({
                "ejercicio": {
                    "id": payload["ejercicio"].id,
                    "enunciado": payload["ejercicio"].enunciado,
                    "dificultad": float(payload["ejercicio"].dificultad)
                },
                "contexto": payload["contexto"],
                "post_url": post_url
            })
        else:
            return render(request, "diagnostico/index.html", {
                "ejercicio": payload["ejercicio"],
                "contexto": payload["contexto"],
                "diagnostico": payload["diagnostico"],
                "remaining_seconds": payload["remaining_seconds"],
                "post_url": post_url
            })
            

    
    @transaction.atomic
    def post(self, request):
        # necesito obtener los pasos y la respuesta del estudiante
        # aceptar application/json con o sin charset
        ct = request.content_type or ""
        if not ct.startswith("application/json"):
            return JsonResponse({"error": "Se esperaba application/json"}, status=400)
        estudiante, err_resp = get_estudiante_from_request(request)
        
        if err_resp:
            return err_resp
        
        # validar diagnostico activo para API
        payload_check, err = prepare_next_payload_diagnostico(estudiante, wants_json=True) #???
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
            
        contexto = select_mode(estudiante,siguiente_ejercicio,"diagnostico")
        
        return json_next_excercise_response(siguiente_ejercicio,contexto,theta=theta_actual,se=se,num_items=num_items)
        
        
        # Cómo determino el umbral del error estándar?
        # por qué 0.4???
        # No lo puedo suponer
        
@method_decorator(login_required,name='dispatch')
class EjercicioView(DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    def get(self, request, ejercicio_id= None):
        if ejercicio_id:            
            ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
            contexto = {"display_text": ejercicio.enunciado, "hint":""}
            return render(request, "ejercicio/ejercicio.html", {"ejercicio": ejercicio, "contexto":contexto})
        # fallback
        estudiante, err = get_estudiante_from_request(request)
        if err:
            return err 
        
        payload, err_resp = prepare_next_payload_normal(estudiante)
        if err_resp:
            messages.error(request, err_resp)
            return redirect('home')
        
        
        ejercicio = payload["ejercicio"]
        contexto = payload["contexto"]
        
        return render(request, "ejercicios/ejercicio.html", {
            "ejercicio": ejercicio,
            "contexto": contexto,
            # "diagnostico": diagnostico,
            # "remaining_seconds": remaining_seconds
        })
    def post(self, request):
        ct = request.content_type or ""
        if not ct.startswith("application/json"):
            return JsonResponse({"error":"Se esperaba application/json"}, status=400)
        
        estudiante, err = get_estudiante_from_request(request)
        if err:
            return err
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error":"Json Inválido"}, status =400)
        
        ejercicio_id = data.get("ejercicio_id")
        respuesta = (data.get("respuesta") or "").strip()#???
        pasos = data.get("pasos", [])
        
        if not ejercicio_id:
            return JsonResponse({"error":"falta id del ejercicio"}, status= 400)
        
        ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
        es_correcto, puntos = evaluar_respuesta(respuesta, ejercicio.solucion)
        
        intento = crear_intento_servidor(estudiante,ejercicio,respuesta,es_correcto,pasos)
        
        logger.info(
            "Intento creado (ejercicios.view)_ intento_id=%s  estudiante=%s ejercicio=%s puntos=%s es_correcto=%s",
            intento.id,estudiante.pk,ejercicio.id,puntos,es_correcto
        )
        
        #Respuesta AJAX (fetch), devolver_intento_id para que el cliente rendirice el resultado
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("json")
        if is_ajax:
            return JsonResponse({
                "success": True,
                "intento_id": intento.id,
                "es_correcto": es_correcto,
                "puntos": puntos
            })
            
            
        # redirigir feedback
        try:
            url = reverse("check-respuesta", kwargs={"intento_id":intento.id})
        except Exception:
            logger.warning("No existe la URL 'check-respuesta' para redirigir, Devolviendo JSON...")
            return JsonResponse({
                "success": True,
                "intento_id": intento.id,
                "es_correcto": es_correcto,
                "puntos":puntos
            })
            
        return redirect(url)
class MatchMakingGroupView(DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    def get(self,request):
        
        return render(request,'ejercicios/matchmaking_group.html')
    
    
    def post(self,request):
        
        pass
    
# No sé si voy a necesitar esta clase la verdad...
# class ContinuarEjercicioGrupal(MatchMakingGroupView,DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    
    
    # GET /ejercicios/check/<int:intento_id>/
@method_decorator(login_required, name='dispatch')
class CheckAnswer(View):
    def get(self,request, intento_id):
        estudiante = getattr(request.user, "estudiante", None)
        if not estudiante:
            return HttpResponseForbidden("Acceso denegado")
        
        intento = get_object_or_404(Intento.objects.select_related("ejercicio","estudiante"), pk=intento_id)
        
        if intento.estudiante_id != estudiante.id and not request.user.is_staff:
            return HttpResponseForbidden("No tienes acceso a este intento")
        
        ejercicio = intento.ejercicio
        
        # esto ya se hace al crear el intento, pero es bueno revalidarlo para seguridad y consistencia
        es_correcto = (normalizar_respuesta(intento.respuesta_estudiante) == normalizar_respuesta(ejercicio.solucion))
        puntos = 1.0 if es_correcto else 0.0
        
        pasos_intento = list(intento.pasos.all())
        pasos_correctos_qs = PasoEjercicio.objects.filter(ejercicio=ejercicio).order_by("orden")
        pasos_correctos = list(pasos_correctos_qs)
        
        feedback = Feedback.objects.filter(intento = intento).order_by("-fecha_feedback").first()
        feedback_pasos = []
        if feedback:
            feedback_pasos = list(FeedbackPasos.objects.filter(feedback=feedback)
                                  .order_by("orden"
                                  .select_related("tipo_feedback")))
            
        contexto = {
            "intento": intento,
            "ejercicio":ejercicio,
            "es_correcto":es_correcto,
            "puntos":puntos,
            "pasos_intento":pasos_intento,
            "pasos_correctos":pasos_correctos,
            "feedback":feedback,
            "feedback_pasos":feedback_pasos,
        }
        
        if request.GET.get("json"):
            # construir dict minimalista
            return JsonResponse({
                "success": True,
                "intento_id": intento.id,
                "es_correcto": es_correcto,
                "puntos": puntos,
                "pasos_intento": [{"orden": p.orden, "contenido": p.contenido} for p in pasos_intento],
                "pasos_correctos": [{"orden": p.orden, "contenido": p.contenido} for p in pasos_correctos],
                "feedback": feedback.feedback if feedback else None
            })

        # Render HTML
        return render(request, "ejercicios/check-respuesta.html", contexto)