from django.shortcuts import render
from django.contrib import messages
from accounts.models import Diagnostico, Estudiante
from ejercicios.utils.text import normalize_text
from .models import Intento,IntentoPaso
from accounts.services import diagnostico_finalizado
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest 
# from django.urls import reverse
# import json
from typing import Tuple, Optional, Dict, Any, List


import logging
logger = logging.getLogger(__name__)

try:
    from ejercicios.services import seleccionar_siguiente_ejercicio
except ImportError as e:
    logger.error("Error al importar servicios: %s", str(e))
    def seleccionar_siguiente_ejercicio(estudiante):
        from ejercicios.models import Ejercicio
        logger.warning("--ERROR-- Usando selección aleatoria | Fallo en importación")
        return Ejercicio.objects.order_by('?').first()
try:
    from .Api_LLMs.requestdiagnostico  import contextualize_exercise_diagnostico
except ImportError as e:
    logger.error("Error al importar request: %s", str(e))
    def contextualize_exercise_diagnostico(ejercicio):
        logger.warning("Módulo requestdiagnostico no disponible | Usando contexto por defecto")
        return {"display_text":ejercicio.enunciado, "hint": "Contexto no disponible"}        

try: 
    from .Api_LLMs.request import contextualize_exercise
except ImportError as e:
    logger.error("Error al importar request: %s", str(e))
    def contextualize_exercise(ejercicio,carrera=None):
        logger.warning('Módulo request no disponible | Usando contexto por defecto')
        return {"display_text": ejercicio.enunciado, "hint": f'Contexto para {carrera or "General"} no disponible'}
    

# Esta la usaré más adelante
def get_type_of_user(request):
    try:
        estudiante = request.user.estudiante
        docente = request.user.docente
    except Exception:
        return None, HttpResponseBadRequest("Usuario no encontrado")

# get y validaciones
def get_estudiante_from_request(request) -> Tuple[Optional[Estudiante], Optional[JsonResponse]]:
    # Devuelve (estudiante,error_response) este ultimo es None si todo está bien
    try:
        return request.user.estudiante,None
    except Exception:
        return None, HttpResponseBadRequest("Usuario no encontrado")
    

def obtener_o_validar_diagnostico(estudiante) -> Diagnostico:
    # logica de services.py
    from accounts.services import obtener_o_validar_diagnostico #Import local, pa evitar ciclos
    return obtener_o_validar_diagnostico(estudiante)

def diagnostico_activo_para_api(estudiante):
    from accounts.services import diagnostico_activo
    return diagnostico_activo(estudiante)

#Es muy probable que vuelva a modificar esta función, pero por ahora queda así
# Seleccionad entre modos: diagnostico, ejercicio (solo) y me falta en grupo
def select_mode(estudiante,ejercicio, modo: str ):
    try:
        if modo == "diagnostico":
            return contextualize_exercise_diagnostico(ejercicio)
        if not estudiante:
            raise ValueError("Se requiere ser estudiante en modo normal")
        # obtener un string representativo de la carrera, preferir un campo explícito
        carrera_obj = getattr(estudiante, "carrera", None)

        if carrera_obj is None:
            carrera_str = "General"
        else:
            # preferir un campo 'nombre' o 'slug' si existe; fallback a str()
            carrera_str = getattr(carrera_obj, "nombre", None) or str(carrera_obj)
            carrera_str = normalize_text(carrera_str, for_storage=True)
        logger.info("Seleccionando modo %s para estudiante %s en carrera %s",
                    modo, estudiante.user.username, carrera_str)
        return contextualize_exercise(ejercicio, carrera_str)

    except Exception as e:
        logger.exception("Error al generar contexto para ejercicio %s en modo %s: %s", 
                         getattr(ejercicio, "id", "?"), modo, str(e))
        return {
            "display_text": ejercicio.enunciado,
            "hint": "Contexto no disponible actualmente"
        }


def prepare_next_payload_diagnostico(estudiante, wants_json:bool = False) -> Tuple[Optional[Dict[str,Any]], Optional[JsonResponse]]:
    # validar diagnostico
    # seleccionar sig ejercicio
    # generar contexto
    
    if wants_json:
        diag = diagnostico_activo_para_api(estudiante)
        if not diag:
            return None, JsonResponse({"error":"El diagnostico ya finalizó o expiró", "finalizado":True},status=403)
        diagnostico = diag
    else:
        diagnostico = obtener_o_validar_diagnostico(estudiante)
        if diagnostico.finalizado or diagnostico.is_expired():
            return {
                "finalizado": True,
                "diagnostico": diagnostico,
                "motivo": "Tiempo agotado" if diagnostico.is_expired() else "Precisión alcanzada"
            }, None
    
    ejercicio = seleccionar_siguiente_ejercicio(estudiante)
    if not ejercicio:
        diagnostico.finalizado = True
        diagnostico.save(update_fields=['finalizado'])
        if wants_json:
            return None , JsonResponse({
                "succes": False,
                "final": True,
                "error": "No hay más ejercicios disponibles",
                "motivo": "No hay más ejercicios disponibles",
            }, status=200)
        return {
            "finalizado": True,
            "diagnostico": diagnostico,
            "motivo": "No hay más ejercicios disponibles"
        }, None

    contexto = select_mode(estudiante,ejercicio, "diagnostico") 

    remaining_seconds = max(0, int(diagnostico.tiempo_restante()))
    
    
    payload = {
        "estudiante": estudiante,
        "diagnostico": diagnostico,
        "ejercicio": ejercicio,
        "contexto": contexto,
        "remaining_seconds": remaining_seconds       
    }
    

    return payload, None


def prepare_next_payload_normal(estudiante) -> Tuple[Optional[Dict[str,Any]], Optional[str]]:
    ejercicio = seleccionar_siguiente_ejercicio(estudiante)
    if not ejercicio:
        return None, "No hay ejercicios disponibles en este momento"
    contexto = select_mode( estudiante, ejercicio, "normal")

    payload = {
        "estudiante": estudiante,
        "ejercicio": ejercicio,
        "contexto": contexto
    }
    return payload, None








def crear_intento_servidor(estudiante, ejercicio,respuesta_estudiante:str, es_correcto: bool, pasos: List[str], diagnostico=None, tiempo_inicio=None,tiempo_fin=None):
    # Crear intento e intento paso usando el tiempo calculado por el servidor
    # devuelve el intento creado
    logger.debug("crear_intento_servidor() — inicio — estudiante=%s ejercicio=%s", getattr(estudiante, 'pk', '?'), getattr(ejercicio, 'id', '?'))

    if tiempo_fin is None: 
        tiempo_fin = timezone.now()
    
    tiempo_en_segundos = 0.0
    if diagnostico:
        try:
            server_remaining = diagnostico.tiempo_restante()
            server_remaining_clamped = max(0.0, float(server_remaining))
            tiempo_en_segundos = float(diagnostico.duracion_segundos) - server_remaining_clamped
        except Exception as e:
            logger.error(
                "Error al calcular tiempo_en_segundos desde diagnostico para estudiante %s y ejercicio %s: %s",
                estudiante.pk, ejercicio.id, str(e)
            )
            tiempo_en_segundos = 0.0
    elif tiempo_inicio:
        try:
            if isinstance(tiempo_inicio,str):
                tiempo_inicio = timezone.datetime.fromisoformat(tiempo_inicio)
            if timezone.is_naive(tiempo_inicio):
                tiempo_inicio = timezone.make_aware(tiempo_inicio, timezone.get_current_timezone())
            tiempo_en_segundos = (tiempo_fin - tiempo_inicio).total_seconds()
            tiempo_en_segundos = max(0.0, tiempo_en_segundos)
        except Exception as e:
            logger.error(
                "Error al calcular tiempo_en_segundos para estudiante %s y ejercicio %s: %s",
                estudiante.pk, ejercicio.id, str(e)
            )
            tiempo_en_segundos = 0.0
    respuesta_norm = (respuesta_estudiante or "")[:150].strip()  # limitar a max length
    if not respuesta_norm and pasos:
        last = None
        for p in reversed(pasos):
            if p and str(p).strip():
                last = str(p).strip()
                break
            respuesta_norm = last or "Sin respuesta"
            
    intento = None
    try:  
        with transaction.atomic():
            intento = Intento.objects.create(
                estudiante=estudiante,
                ejercicio=ejercicio,
                respuesta_estudiante=respuesta_norm, #limitar a max length
                es_correcto=es_correcto,
                puntos=1.0 if es_correcto else 0.0,
                tiempo_en_segundos=tiempo_en_segundos,
                fecha_intento=tiempo_fin
            )
            intento.save()
            logger.info("Intento %s creado para estudiante %s en ejercicio %s", intento.id, estudiante.pk, ejercicio.id)
        
            for orden, paso_texto in enumerate(pasos or [], start=1):
                try:
                    IntentoPaso.objects.create(
                        intento=intento,
                        orden=orden,
                        contenido=paso_texto,
                        datos_aux={}
                    )
                    logger.info("  Paso %s creado para intento %s", orden, intento.id)
                except Exception as e:
                    logger.error(
                        "Error al crear intento o pasos para estudiante %s en ejercicio %s: %s",
                        estudiante.pk, ejercicio.id, str(e)
                    )
    except Exception as e:
        logger.error(
            "Error al crear intento para estudiante %s en ejercicio %s: %s",
            estudiante.pk, ejercicio.id, str(e)
        )
        try:
            q = Intento.objects.filter(
                estudiante=estudiante,
                ejercicio=ejercicio,
                respuesta_estudiante=(respuesta_estudiante or "")[:150],
            ).order_by('-fecha_intento')
            intento = q.first()
            if intento:
                logger.info("Recuperado intento existente %s para estudiante %s en ejercicio %s tras error en creación", intento.id, estudiante.pk, ejercicio.id)
                return intento
        except Exception as e2:
            logger.error(
                "Error al recuperar intento existente para estudiante %s en ejercicio %s: %s",
                estudiante.pk, ejercicio.id, str(e2)
            )
            intento = None
            return None
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


def json_next_excercise_response(ejercicio, contexto, theta=None, se=None, num_items=None):
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