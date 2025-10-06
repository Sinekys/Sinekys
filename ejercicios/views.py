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
# from django.urls import reverse
import json
import re
import numpy

# Models
from ejercicios.models import Ejercicio, Intento, IntentoPaso, EjercicioVecesMostrado
from accounts.models import Estudiante, Diagnostico

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

@method_decorator(login_required, name='dispatch') #Verifica si está loggeado
class DiagnosticTestView(View):
    
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self._get_json_response(request)
        else:
            return self._get_html_response(request)
        
    def _get_html_response(self, request):
        try:
            estudiante = request.user.estudiante
            ejercicio = seleccionar_siguiente_ejercicio(estudiante)
        except Estudiante.DoesNotExist:
            return HttpResponseBadRequest('Usuario no encontrado')
        
        if not ejercicio:
            return JsonResponse({"error": "No hay ejercicios disponibles"}, status=400)
        
        contexto = contextualize_exercise_diagnostico(ejercicio)
        context = {
            "ejercicio": ejercicio,
            "contexto": contexto,
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
    
    # def get_absolute_url(self):
    #     return reverse('events:event-detail', kwargs={'pk':self.pk})
    
    

    
    
    @transaction.atomic #Debo documentar esto, es para asegurar consistencia en los datos
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
        
        diagnostico, created = Diagnostico.objects.get_or_create(
            estudiante=estudiante,
            defaults={
                'theta':0.0,
                'error_estimacion':1.0,
                'finalizado':False
            }
        )
        
        # Verificar si el exámen ya finalizó o expiró
        
        if diagnostico.finalizado or diagnostico.is_expired(): 
            return JsonResponse({
            "success": True,
            "final": True,
            "motivo": "Diagnostico ya finalizado o tiempo agotado",
            "mensaje":"Respuesta registrada correctamente"
        })
        
        # payload para los ejercicios
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
            
              # Si no finaliza, devolver siguiente ejercicio
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

        contexto = {
            "display_text": siguiente_ejercicio.enunciado,
            "hint": "Pista aquí"
        }

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