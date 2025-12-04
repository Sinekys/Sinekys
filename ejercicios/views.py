from django.views import View
from django.utils.decorators import method_decorator

from django.shortcuts import render,get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, Http404,HttpResponseNotAllowed
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from usage.services import can_user_attempt, register_attempt





import ast
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
from ejercicios.ia_feedback import save_ai_feedback_intento
from ejercicios.Api_LLMs.requestfeedback import call_my_ai_service
# logs
import logging
logger = logging.getLogger(__name__)

# Mixins creados
from .mixins import (
    _diag_session_key,
    _ejercicio_session_key,
    get_estudiante_from_request,
    prepare_next_payload_diagnostico,
    prepare_next_payload_normal,
    crear_intento_servidor,
    # render_diagnostico_template,
    json_next_excercise_response,   
    obtener_o_validar_diagnostico, 
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
        diagnostico = obtener_o_validar_diagnostico(estudiante)
        if diagnostico.finalizado or diagnostico.is_expired():
            return render(request, "diagnostico/finalizado.html",{
                "finalizado": True,
                "diagnostico": diagnostico,
                "motivo": "Tiempo agotado" if diagnostico.is_expired else "Precisión alcanzada"
            })
        session_key = _diag_session_key(diagnostico)
        ejercicio = None
        ejercicio_id_reserved = request.session.get(session_key)
        if ejercicio_id_reserved:
            try:
                ejercicio = Ejercicio.objects.get(pk=int(ejercicio_id_reserved))
            except Ejercicio.DoesNotExist:
                request.session.pop(session_key,None)
                ejercicio = None
        if not ejercicio:
            ejercicio = seleccionar_siguiente_ejercicio(estudiante)
            if not ejercicio:
                diagnostico.finalizado = True
                diagnostico.save(update_fields=['finalizado'])
                return render(request, "diagnostico/finalizado.html", {
                    "finalizado": True,
                    "diagnostico": diagnostico,
                    "motivo": "No hay más ejercicios disponibles"
                })
            # Reservamos en sesión: ahora GET repetido devolverá mismo ejercicio
            request.session[session_key] = ejercicio.id
        contexto = select_mode(estudiante, ejercicio,"diagnostico")
        remaining_seconds= max(0,int(diagnostico.tiempo_restante()))
        payload = {
            "ejercicio": ejercicio,
            "contexto": contexto,
            "diagnostico": diagnostico,
            "remaining_seconds": remaining_seconds
        }
        # payload, err = prepare_next_payload_diagnostico(estudiante, wants_json=wants_json)
        

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

        client_remaining = data.get("remaining_seconds")
        
        if not ejercicio_id:
            return JsonResponse({"error":"Falta id del ejercicio"}, status=400)
        
        ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
        es_correcto, puntos = evaluar_respuesta(respuesta_estudiante, ejercicio.solucion)
        
        server_remaining = max(0.0, float(diagnostico.tiempo_restante()))
        client_remaining_float = None
        if client_remaining is not None:
            try:
                client_remaining_float = float(client_remaining)
                if abs(client_remaining_float - server_remaining) > 5:
                    logger.warning(
                        "Client-reported remaining (%s) differs from server (%s) for diagnostico %s / estudiante %s",
                        client_remaining_float, server_remaining, diagnostico.id, estudiante.pk
                    )
            except (TypeError, ValueError):
                pass
    #    comprobación extra por si expiró entre peticiones
        if diagnostico.is_expired():
            diagnostico.finalizado = True
            diagnostico.save(update_fields=["finalizado"])
            return JsonResponse({"success": True, "final":True,"motivo":"Tiempo agotado antes del envío"}, status=200)
        
        intento = crear_intento_servidor(
            estudiante= estudiante,
            ejercicio=ejercicio,
            respuesta_estudiante=respuesta_estudiante,
            es_correcto=es_correcto,
            pasos=pasos,
            diagnostico=diagnostico)
        logger.info(
            "Intento creado (ejercicios.view - diagnostico) intento_id=%s  estudiante=%s ejercicio=%s puntos=%s es_correcto=%s",
            intento.id,estudiante.pk,ejercicio.id,puntos,es_correcto
        )
        
        
        try: 
            ai_payload = {
                "enunciado": ejercicio.enunciado,
                "respuesta_estudiante": respuesta_estudiante,
                "solucion": ejercicio.solucion,
                "pasos": pasos
            }
            ai_result = call_my_ai_service(ai_payload)
        except Exception as e:
            logger.exception("Error llamando IA para intento %s: %s", intento.id, str(e))
            ai_result = None
        
        if ai_result:
            contexto_ia = ai_result.get("texto") or ai_result.get("contexto") or ""
            feedback_json = ai_result.get("feedback_json") or ai_result.get("correccion") or {}
            pasos_feedback = ai_result.get("pasos")  # opcional
            save_ai_feedback_intento(
                intento=intento,
                contexto_ia=contexto_ia,
                feedback_json=feedback_json,
                fuente="chatgpt",
                pasos_feedback=pasos_feedback
            )
        
        
        
        # actualizar dianostico y obtener theta + SE
        theta_actual, se = actualizar_diagnostico(estudiante)
        # actualizar el objeto Diagnostico con los nuevos valores
        diagnostico.theta = theta_actual
        diagnostico.error_estimacion = se
        diagnostico.save(update_fields=["theta","error_estimacion"])
        
        # criterios de finalizacion
        # criterios de finalizacion
        # criterios de finalizacion
        num_items = Intento.objects.filter(estudiante=estudiante).count() #Ojo puede haber un problema, ya que si el es estudiante cancela la prueba, los intentos seguiran registrados y por lo tanto el número aumentaría
        max_items = 2 # CAMBIAR A 30 CAMBIAR A 30 CAMBIAR A 30 CAMBIAR A 30 CAMBIAR A 30 CAMBIAR A 30
        umbral_se = 0.4
        
        
        finalizado = (
            se<umbral_se or
            num_items>=max_items or
            diagnostico.is_expired() or
            (abs(theta_actual) >= 2.9 and num_items >=10)
        )
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
        elif abs(theta_actual) >= 2.9 and num_items >= 10:
            motivo = "Nivel extremo detectado"

        session_key = _diag_session_key(diagnostico)
        if finalizado:
            diagnostico.finalizado = True
            diagnostico.save(update_fields=["finalizado"])
            request.session.pop(session_key,None)
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
            request.session.pop(session_key,None)
            return JsonResponse({
                "success": True,
                "final": True,
                "motivo": "No hay más ejercicios disponibles",
                "theta": theta_actual,
                "error": se
            })
        request.session[session_key] = siguiente_ejercicio.id
        contexto = select_mode(estudiante,siguiente_ejercicio,"diagnostico")
        
        return json_next_excercise_response(siguiente_ejercicio,contexto,theta=theta_actual,se=se,num_items=num_items)
        
        
        # Cómo determino el umbral del error estándar?
        # por qué 0.4???
        # No lo puedo suponer
        
@method_decorator(login_required,name='dispatch')
class EjercicioView(DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    def get(self, request, ejercicio_id= None):
        estudiante, err = get_estudiante_from_request(request)
        if ejercicio_id:            
            ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
            request.session[_ejercicio_session_key(estudiante)] = ejercicio.id 
            request.session[f"tiempo_inicio_ejercicio_{ejercicio.id}"] = timezone.now().isoformat()
            contexto = {"display_text": ejercicio.enunciado, "hint":""}
            return render(request, "ejercicio/ejercicio.html", {"ejercicio": ejercicio, "contexto":contexto,"ejercicio_id":ejercicio.id})
        
        
        session_key = _ejercicio_session_key(estudiante)
        ejercicio = None
        ejercicio_id_reserved = request.session.get(session_key)
        if ejercicio_id_reserved:
            try: 
                ejercicio = Ejercicio.objects.get(pk=int(ejercicio_id_reserved))
            except Ejercicio.DoesNotExist:
                request.session.pop(session_key,None)
                ejercicio = None
        if not ejercicio:
            payload, err_resp = prepare_next_payload_normal(estudiante)
            if err_resp:
                messages.error(request, err_resp)
                return redirect('home')
            
            ejercicio = payload["ejercicio"]
            contexto = payload["contexto"]
            request.session[session_key] = ejercicio.id
        else:
            contexto = select_mode(estudiante, ejercicio, "normal")
        
            
        # Tiempo en contestar
        request.session[f"tiempo_inicio_ejercicio_{ejercicio.id}"] = timezone.now().isoformat()
        
        return render(request, "ejercicios/ejercicio.html", {
            "ejercicio": ejercicio,
            "contexto": contexto,
            "ejercicio_id": ejercicio.id,
        })
    @transaction.atomic
    def post(self, request):
        ct = request.content_type or ""
        if not ct.startswith("application/json"):
            return JsonResponse({"error": "Se esperaba application/json"}, status=400)
    
        estudiante, err = get_estudiante_from_request(request)
        if err:
            return err
    
        # ============================
        # 🔒 LÍMITE DIARIO DE INTENTOS
        # ============================
        from usage.services import can_user_attempt, register_attempt
        can_attempt, limit, used = can_user_attempt(request.user)
    
        if not can_attempt:
            return JsonResponse({
                "error": "Has alcanzado tu límite diario de intentos.",
                "limite": limit,
                "usados": used
            }, status=403)
    
        # Si pasa el límite → registra un intento consumido
        register_attempt(request.user)
        # ============================
    
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Json Inválido"}, status=400)
    
        ejercicio_id = data.get("ejercicio_id")
        respuesta = (data.get("respuesta") or "").strip()
        pasos = data.get("pasos", [])
    
        if not ejercicio_id:
            return JsonResponse({"error": "falta id del ejercicio"}, status=400)
    
        ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
        es_correcto, puntos = evaluar_respuesta(respuesta, ejercicio.solucion)
    
        tiempo_inicio_iso = request.session.get(f"tiempo_inicio_ejercicio_{ejercicio.id}")
        tiempo_fin = timezone.now()
    
        tiempo_inicio = None
        if tiempo_inicio_iso:
            try:
                tiempo_inicio = timezone.datetime.fromisoformat(tiempo_inicio_iso)
                if timezone.is_naive(tiempo_inicio):
                    tiempo_inicio = timezone.make_aware(tiempo_inicio, timezone.get_current_timezone())
            except Exception as e:
                logger.warning(
                    "Error al calcular tiempo_en_segundos para estudiante %s y ejercicio %s: %s",
                    estudiante.pk, ejercicio.id, str(e)
                )
    
        intento = crear_intento_servidor(
            estudiante=estudiante,
            ejercicio=ejercicio,
            respuesta_estudiante=respuesta,
            es_correcto=es_correcto,
            pasos=pasos,
            tiempo_inicio=tiempo_inicio,
            tiempo_fin=tiempo_fin
        )
    
        if not intento:
            logger.error("Error al crear intento para estudiante %s en ejercicio %s", estudiante.pk, ejercicio.id)
            return JsonResponse({"error": "Error interno al crear el intento"}, status=500)
    
        request.session.pop(_ejercicio_session_key(estudiante),None)        
        request.session.pop(f"tiempo_inicio_ejercicio_{ejercicio.id}", None)
        logger.info(
            "Intento creado (ejercicios.view)_ intento_id=%s  estudiante=%s ejercicio=%s puntos=%s es_correcto=%s",
            intento.id, estudiante.pk, ejercicio.id, puntos, es_correcto
        )
        try: 
            ai_payload = {
                "enunciado": ejercicio.enunciado,
                "respuesta_estudiante": respuesta,
                "solucion": ejercicio.solucion,
                "pasos": pasos
            }
            ai_result = call_my_ai_service(ai_payload)
        except Exception as e:
            logger.exception("Error llamando IA para intento %s: %s", intento.id, str(e))
            ai_result = None
        
        if ai_result:
            contexto_ia = ai_result.get("texto") or ai_result.get("contexto") or ""
            feedback_json = ai_result.get("feedback_json") or ai_result.get("correccion") or {}
            pasos_feedback = ai_result.get("pasos")  # opcional
            save_ai_feedback_intento(
                intento=intento,
                contexto_ia=contexto_ia,
                feedback_json=feedback_json,
                fuente="chatgpt",
                pasos_feedback=pasos_feedback
            )
        
        
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("json")
        redirect_url = reverse("check-respuesta", kwargs={"intento_uuid": intento.uuid})
        if is_ajax:
            return JsonResponse({
                "success": True,
                "intento_id": intento.id,
                "es_correcto": es_correcto,
                "puntos": puntos,
                "redirect_url": redirect_url
            })
    
        return redirect(redirect_url)
    
    #@transaction.atomic        
    #def post(self, request):
    #    ct = request.content_type or ""
    #    if not ct.startswith("application/json"):
    #        return JsonResponse({"error":"Se esperaba application/json"}, status=400)
    #    
    #    estudiante, err = get_estudiante_from_request(request)
#    #    if err:
#    #        return err
#    #
    #    try:
    #        data = json.loads(request.body)
    #    except json.JSONDecodeError:
    #        return JsonResponse({"error":"Json Inválido"}, status =400)
    #    
    #    ejercicio_id = data.get("ejercicio_id")
    #    respuesta = (data.get("respuesta") or "").strip()
    #    pasos = data.get("pasos", [])
    #    
    #    
    #    if not ejercicio_id:
    #        return JsonResponse({"error":"falta id del ejercicio"}, status= 400)
    #    
    #    ejercicio = get_object_or_404(Ejercicio, pk=ejercicio_id)
    #    es_correcto, puntos = evaluar_respuesta(respuesta, ejercicio.solucion)
    #    
    #    tiempo_inicio_iso = request.session.get(f"tiempo_inicio_ejercicio_{ejercicio.id}")
    #    tiempo_inicio = None
    #    tiempo_fin = timezone.now()
    #    
    #    # tiempo_en_segundos = 0.0
    #    if tiempo_inicio_iso:
    #        try:
    #            tiempo_inicio = timezone.datetime.fromisoformat(tiempo_inicio_iso)
    #            if timezone.is_naive(tiempo_inicio):
    #                tiempo_inicio = timezone.make_aware(tiempo_inicio, timezone.get_current_timezone())
    #        except Exception as e:
    #            logger.warning(
    #                "Error al calcular tiempo_en_segundos para estudiante %s y ejercicio %s: %s",
    #                estudiante.pk, ejercicio.id, str(e)
    #            )
    #    
    #    intento = crear_intento_servidor(
    #        estudiante=estudiante,
    #        ejercicio=ejercicio,
    #        respuesta_estudiante=respuesta,
    #        es_correcto=es_correcto,
    #        pasos=pasos,
    #        tiempo_inicio=tiempo_inicio,
    #        tiempo_fin=tiempo_fin)
    #    
    #    if not intento:
#    #        logger.error("Error al crear intento para estudiante %s en ejercicio %s", estudiante.pk, ejercicio.id)
#    #        return JsonResponse({"error":"Error interno al crear el intento"}, status=500)
#    #
    #    request.session.pop(f"tiempo_inicio_ejercicio_{ejercicio.id}", None)
    #    
    #    logger.info(
    #        "Intento creado (ejercicios.view)_ intento_id=%s  estudiante=%s ejercicio=%s puntos=%s es_correcto=%s",
    #        intento.id,estudiante.pk,ejercicio.id,puntos,es_correcto
    #    )
    #    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("json")
    #    redirect_url = reverse("check-respuesta", kwargs={"intento_id": intento.id})
    #    if is_ajax:
    #        return JsonResponse({
    #            "success": True,
    #            "intento_id": intento.id,
    #            "es_correcto": es_correcto,
    #       #     "puntos": puntos,
    #       #     "redirect_url": redirect_url
    #       # })
#
    #    return redirect(redirect_url)
    #            
    #    # return redirect(url)
class MatchMakingGroupView(DiagnosticoCompletadoMixin,LoginRequiredMixin,View):
    def get(self,request):
        
        return render(request,'ejercicios/matchmaking_group.html')
    
    
    def post(self,request):
        
        pass


logger = logging.getLogger(__name__)

def _parse_feedback_raw(raw_fb):
    """
    Convierte un feedback crudo (puede ser dict, JSON-string, o repr(dict)) a dict seguro.
    Retorna (parsed_dict, error_str_or_None)
    """
    if raw_fb is None:
        return {}, None

    # Si ya es dict, devolvemos tal cual
    if isinstance(raw_fb, dict):
        return raw_fb, None

    # Si es bytes -> decode
    if isinstance(raw_fb, (bytes, bytearray)):
        try:
            raw_fb = raw_fb.decode('utf-8', errors='ignore')
        except Exception:
            raw_fb = str(raw_fb)

    # Si es string, probamos JSON, luego ast.literal_eval, luego intento extraer entre llaves
    if isinstance(raw_fb, str):
        # Intento 1: JSON válido
        try:
            parsed = json.loads(raw_fb)
            if isinstance(parsed, dict):
                return parsed, None
        except Exception:
            pass

        # Intento 2: literal_eval (parsea "{'a':1}" a dict)
        try:
            parsed = ast.literal_eval(raw_fb)
            if isinstance(parsed, dict):
                return parsed, None
        except Exception:
            pass

        # Intento 3: extraer bloque {...} y reintentar JSON
        start = raw_fb.find('{')
        end = raw_fb.rfind('}') + 1
        if start != -1 and end != -1 and end > start:
            fragment = raw_fb[start:end]
            try:
                parsed = json.loads(fragment)
                if isinstance(parsed, dict):
                    return parsed, None
            except Exception:
                # como último recurso, intentamos literal_eval
                try:
                    parsed = ast.literal_eval(fragment)
                    if isinstance(parsed, dict):
                        return parsed, None
                except Exception:
                    pass

    # Si nada funcionó, devolvemos {} y el raw para debugging
    return {}, f"Could not parse feedback (type={type(raw_fb)}); returning empty dict."


    


@method_decorator(login_required, name='dispatch')
class CheckAnswer(View):
    def get(self, request, intento_uuid):
        try:
            estudiante = request.user.estudiante
        except AttributeError:
            messages.error(request, "No tienes permiso para acceder a esta página")
            return redirect('')

        intento = get_object_or_404(
            Intento.objects.select_related("ejercicio", "estudiante"),
            uuid=intento_uuid
        )

        if intento.estudiante_id != estudiante.id and not request.user.is_staff:
            home_url = reverse('mainPage')
            html = (
                '<!doctype html><html><head>'
                f'<meta http-equiv="refresh" content="3;url={home_url}">'
                '<meta charset="utf-8"></head><body>'
                '<p>No tienes acceso a este intento. Serás redirigido a la página principal en 3 segundos.</p>'
                f'<p>Si no, <a href="{home_url}">haz clic aquí</a>.</p>'
                '</body></html>'
            )
            return HttpResponseForbidden(html)

        ejercicio = intento.ejercicio

        es_correcto, puntos = evaluar_respuesta(intento.respuesta_estudiante, ejercicio.solucion)

        pasos_intento = list(intento.pasos.all().order_by('orden'))

        pasos_correctos_qs = PasoEjercicio.objects.filter(ejercicio=ejercicio).order_by("orden")
        pasos_correctos = list(pasos_correctos_qs)

        feedback = Feedback.objects.filter(intento=intento).order_by("-fecha_feedback").first()
        feedback_pasos = []
        if feedback:
            feedback_pasos = list(
                FeedbackPasos.objects.filter(feedback=feedback).select_related("tipo_feedback").order_by("orden")
            )

        # --- Normalizar feedback para la plantilla ---
        feedback_parsed = {}
        feedback_parse_error = None
        feedback_raw = None

        if feedback:
            # asumo que el campo se llama 'feedback' en el modelo; puede ser TextField o JSONField
            feedback_raw = getattr(feedback, 'feedback', None)
            parsed, err = _parse_feedback_raw(feedback_raw)
            feedback_parsed = parsed or {}
            feedback_parse_error = err

        contexto = {
            "intento": intento,
            "ejercicio": ejercicio,
            "es_correcto": es_correcto,
            "puntos": puntos,
            "pasos_intento": pasos_intento,
            "pasos_correctos": pasos_correctos,
            "feedback": feedback,                  # objeto DB (por si lo necesitas en template)
            "feedback_parsed": feedback_parsed,    # dict seguro para iterar en template
            "feedback_raw": feedback_raw,          # raw (debug)
            "feedback_parse_error": feedback_parse_error,
            "feedback_pasos": feedback_pasos,
        }

        # JSON endpoint (útil para debugging o front-end async)
        if request.GET.get("json"):
            return JsonResponse({
                "success": True,
                "intento_id": intento.id,
                "es_correcto": es_correcto,
                "puntos": puntos,
                "pasos_intento": [{"orden": p.orden, "contenido": p.contenido} for p in pasos_intento],
                "pasos_correctos": [{"orden": p.orden, "contenido": p.contenido} for p in pasos_correctos],
                "feedback_raw": feedback_raw,
                "feedback_parsed": feedback_parsed,
                "feedback_pasos": [
                    {
                        "orden": fp.orden,
                        "contenido": fp.contenido,
                        "tipo_feedback": fp.tipo_feedback.nombre if fp.tipo_feedback else None
                    } for fp in feedback_pasos
                ]
            })

        # Render HTML
        return render(request, "ejercicios/check-respuesta.html", contexto)
    
    # https://www.sympy.org/es/
    # CALCULADORA/MUESTRA DE SIGNOS MATEMÁTICOS