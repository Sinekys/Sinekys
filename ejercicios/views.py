# ejercicios/views.py
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone
import json
import re
import numpy
# Models
from ejercicios.models import Ejercicio, Intento, IntentoPaso, EjercicioVecesMostrado
from accounts.models import Estudiante

# API ChatGPT
# from request import contextualize_exercise
from .requestdiagnostico import contextualize_exercise_diagnostico

# Fórmulas
from ejercicios.services import actualizar_diagnostico, seleccionar_siguiente_ejercicio



# Normalizar respuesta
#  2X === 2x
def normalizar_respuesta(respuesta: str) -> str:
    if respuesta is None:
        return ""
    
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
    # Vale, necesito una fórmula para ver cuantos puntos se le da al alumno
    # Base:
    # Si el resultado es correcto se le da: 0.X cantidad de puntos
    # Si el resultado es correcto pero el desarrollo está mal se le da 0.Y donde 0.Y < 0.X
    # Si el resultado es incorrecto no se le da puntos 0.0 
    puntos = 1.0 if es_correcto else 0.0
    return (es_correcto, puntos)

@method_decorator(login_required, name='dispatch') #Verifica si está loggeado
class DiagnosticTestView(View):
    
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self._get_json_response(request)
        else:
            return self._get_html_response(request)
        
    def _get_html_response(self,request):
        try:
            estudiante = request.user.estudiante
            ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        except Estudiante.DoesNotExist:
            return HttpResponseBadRequest('Usuario no encontrado x_x')
        
        if not ejercicio:
            return JsonResponse({"error":"Por algún motivo no hay ejercicio disponibles"},status=400)
            
        # LLM contextualización
        contexto = contextualize_exercise_diagnostico(ejercicio) #ojo es diferente a contextualize_excercise
        
        context = {
            "ejercicio": ejercicio, #user {{ ejercicio.id}} en el template
            "contexto": contexto, #respuesta 
        }
        return render(request, "diagnostico/index.html", context)
    
    
    def _get_json_response(self, request):
        try:
            estudiante = request.user.estudiante
            ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        except Estudiante.DoesNotExist:
            return HttpResponseBadRequest('Usuario no encontrado x_x')
        
        if not ejercicio:
            return JsonResponse({"error":"Por algún motivo no hay ejercicio disponibles D:"},status=400)
        
        contexto = {
            "display_text": ejercicio.enunciado,
            "hint": f"Pista aquí"
        }
        return JsonResponse({
                "ejercicio": {
                "id":ejercicio.id,
                "enunciado": ejercicio.enunciado,
                "dificultad": float(ejercicio.dificultad)
            },
            "contexto":contexto
            })
    
    

    
    
    @transaction.atomic #Debo documentar esto, es para asegurar consistencia en los datos
    def post(self, request):
        # necesito obtener los pasos y la respuesta del estudiante
        if request.content_type != "application/json":
            return JsonResponse({"error": "Se esparaba json"}, 400)
        
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error":"Json inválido"}, 400)
        
        try:
            estudiante = request.user.estudiante
        except Estudiante.DoesNotExist:
            return JsonResponse({"error":"Estudiante no encontrado"}, 400)
        
        ejercicio_id = payload.get("ejercicio_id")
        respuesta_estudiante = payload.get("respuesta_estudiante", "").strip()
        tiempo_en_segundos = float(payload.get("tiempo_en_segundos",0))
        pasos = payload.get("pasos", []) #lista de strings
        
        
        if not ejercicio_id:
            return JsonResponse({"error":"Falta id del ejercicio"}, status=400)
        
        ejercicio = get_object_or_404(Ejercicio, pk = ejercicio_id)
        
        # evaluar
        es_correcto, puntos = evaluar_respuesta(respuesta_estudiante, ejercicio.solucion)
        
        # Crwar intento
        intento = Intento.objects.create(
            estudiante=estudiante,
            ejercicio=ejercicio,
            respuesta_estudiante=respuesta_estudiante,
            es_correcto=es_correcto,
            puntos=puntos,
            tiempo_en_segundos=tiempo_en_segundos,
            fecha_intento=timezone.now()
        )
        
        EjercicioVecesMostrado
        
        for orden, paso_texto in enumerate(pasos, start=1):
            IntentoPaso.objects.create(
                intento=intento,
                orden=orden,
                contenido=paso_texto,
                datos_aux={} #futuro variables intermedias?
            )
            
        theta_actual = actualizar_diagnostico(estudiante)
        
        return JsonResponse({
            "success": True,
            "intento_id": intento.id,
            "es_correcto": es_correcto,
            "puntos": puntos,
            "theta": theta_actual,
            "mensaje":"Respuesta registrada correctamente"
        })
        
        # Cómo determino el umbral del error estándar?
        # No lo puedo suponer, no lo voy a hacer