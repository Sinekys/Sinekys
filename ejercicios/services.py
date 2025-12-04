# Aca va todo lo referente a formulas
# Aca va todo lo referente a formulas
# Aca va todo lo referente a formulas
# Aca va todo lo referente a formulas
# básicamente:
    # Si el código usa request, JsonResponse, render, HttpResponse, no va en services.py, probar en mixins
    # Si el código calcula, decide, filtra, transforma datos, sí va en services.py. 

import logging
from random import random

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit  # sigmoid numéricamente estable
from django.db import transaction

from accounts.models import Diagnostico
from .models import Intento, Ejercicio

logger = logging.getLogger(__name__)


def actualizar_diagnostico(estudiante):
    # Estimar theta y su SE usando el modelo Rasch (1PL).
    # Devuelve (theta_estimado, se).
    # Implementación vectorizada, con bounds en [-3,3], manejo de fallos y logging.
    
    intentos_qs = Intento.objects.filter(estudiante=estudiante).select_related("ejercicio")
    if not intentos_qs.exists():
        return 0.0, 1.0  # theta neutro, error grande por defecto

    # Extraer datos en arrays vectorizados
    b_list = []
    y_list = []
    for intento in intentos_qs:
        b_list.append(float(intento.ejercicio.dificultad))
        y_list.append(1 if intento.es_correcto else 0)
    b_arr = np.array(b_list, dtype=float)
    y_arr = np.array(y_list, dtype=float)

    # función de log-verosimilitud (retorna valor positivo = LL)
    def log_likelihood(theta_array):
        theta = float(theta_array[0])
        z = theta - b_arr
        # estabilidad numérica: expit es la sigmoid estable
        p = expit(z)  # valores en (0,1)
        # evitar logs de 0 usando log/present functions
        ll_terms = np.where(y_arr == 1, np.log(p), np.log1p(-p))  # log(p) o log(1-p)
        return float(np.sum(ll_terms))

    # como minimize() minimiza, minimizamos la negativa de la log-verosimilitud
    def neg_log_like(theta_array):
        return -log_likelihood(theta_array)

    # limites para theta
    bounds = [(-3.0, 3.0)]

    # ejecutar optimización
    try:
        result = minimize(
            fun=neg_log_like,
            x0=[0.0],
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 200}
        )
    except Exception as e:
        logger.exception("Error durante la optimización de theta para estudiante %s: %s", getattr(estudiante, 'pk', '?'), e)
        # fallback seguro
        theta_estimado = 0.0
        se = 1.0
        # guardar y salir
        with transaction.atomic():
            Diagnostico.objects.update_or_create(
                estudiante=estudiante,
                defaults={"theta": theta_estimado, "error_estimacion": se}
            )
        return theta_estimado, se

    # comprobar éxito de la optimización
    if not getattr(result, "success", False):
        logger.warning("Optimización no convergió para estudiante %s: message=%s, fun=%s", getattr(estudiante, 'pk', '?'), getattr(result, "message", ""), getattr(result, "fun", None))
        # fallback razonable: usar x0 o el mejor valor encontrado
        try:
            theta_candidate = float(result.x[0])
        except Exception:
            theta_candidate = 0.0
    else:
        theta_candidate = float(result.x[0])

    # asegurar rango final
    theta_estimado = float(np.clip(theta_candidate, -3.0, 3.0))

    # Calcular información total (Fisher) para 1PL: sum p(1-p)
    try:
        z_final = theta_estimado - b_arr
        p_final = expit(z_final)
        info_terms = p_final * (1.0 - p_final)  # a=1 en 1PL
        info_total = float(np.sum(info_terms))

        if info_total < 0.1:
            logger.warning(f"Poca información para estudiante {estudiante.pk}: info_total={info_total}")
            theta_estimado = 0.0 #neutral
            se = 1.5 #error alto por falta de información
            
        # si info_total es 0 o muy pequeño, evitar dividir por 0
        elif info_total <= 0 or np.isclose(info_total, 0.0):
            logger.warning("Información total muy pequeña (<=0) para estudiante %s: info_total=%s, n_items=%d", getattr(estudiante, 'pk', '?'), info_total, len(b_arr))
            se = 1.0
        else:
            se = 1.0 / np.sqrt(info_total)
            # protecciones estándares para SE no pregunten por qué, asi está la documentacion en varios sitios 
            se = float(np.clip(se, 0.2, 2.0))
    except Exception as e:
        logger.exception("Error calculando SE para estudiante %s: %s", getattr(estudiante, 'pk', '?'), e)
        se = 1.0

    # guardar en DB
    try:
        with transaction.atomic():
            Diagnostico.objects.update_or_create(
                estudiante=estudiante,
                defaults={"theta": theta_estimado, "error_estimacion": se}
            )
    except Exception as e:
        logger.exception("No se pudo guardar Diagnostico para estudiante %s: %s", getattr(estudiante, 'pk', '?'), e)

    return theta_estimado, se


def seleccionar_siguiente_ejercicio(estudiante):
    """
    Selecciona el siguiente ejercicio basado en máxima información bajo 1PL:
    I_i(theta) = P(1-P) con P = sigmoid(theta - b).
    Implementación vectorizada que excluye ejercicios previamente respondidos.
    """
    theta = 0.0
    try:
        if hasattr(estudiante, "diagnostico") and estudiante.diagnostico:
            theta = float(estudiante.diagnostico.theta)
    except Exception:
        # fallback
        theta = 0.0

    # evitar repetir items
    intentos_previos = Intento.objects.filter(estudiante=estudiante)
    ids_respondidos = intentos_previos.values_list("ejercicio_id", flat=True)

    disponibles_qs = Ejercicio.objects.exclude(id__in=ids_respondidos)

    # Si no hay disponibles, retornar aleatorio (o None)
    if not disponibles_qs.exists():
        return Ejercicio.objects.order_by("?").first()

    # Extraer arrays de ids y b
    # Materializar queryset para indexar después
    disponibles = list(disponibles_qs)
    ids = [item.id for item in disponibles] # ojo aquí
    b_arr = np.array([float(item.dificultad) for item in disponibles], dtype=float)

    # calcular probabilidad e información vectorialmente
    z = theta - b_arr
    p = expit(z)
    info_arr = p * (1.0 - p)  # 1PL: a=1

    # elegir el índice con máxima información
    try: 
        max_info = float(np.max(info_arr))
        candidates = np.where(np.isclose(info_arr, max_info, atol=1e-12))[0]
        if len(candidates) > 1:
            logger.info("Múltiples candidatos con info máxima para estudiante %s: theta=%.4f, max_info=%.6f, n_candidates=%d", getattr(estudiante, 'pk', '?'), theta, max_info, len(candidates))
            max_idx = int(np.random.choice(candidates))
        else: 
            max_idx = int(np.argmax(info_arr))
    except Exception as e:
        logger.exception("Error seleccionando siguiente ejercicio para estudiante %s: %s", getattr(estudiante, 'pk', '?'), e)
        return random.choice(disponibles)
    
    mejor_item = disponibles[max_idx]
    if mejor_item.id in ids_respondidos:
        logger.error("Error lógico: se seleccionó un ejercicio ya respondido para estudiante %s: ejercicio_id=%s", getattr(estudiante, 'pk', '?'), mejor_item.id)
        for item in disponibles:
            if item.id not in ids_respondidos:
                logger.info("Seleccionando ejercicio no respondido alternativo para estudiante %s: ejercicio_id=%s", getattr(estudiante, 'pk', '?'), item.id)
                return item
            else:
                mejor_item = random.choice(disponibles)
                logger.info("Seleccionando ejercicio aleatorio para estudiante %s: ejercicio_id=%s", getattr(estudiante, 'pk', '?'), mejor_item.id)
    return mejor_item


# Vale hice una prueba con el nuevo modelo y me dio un theta de 3, lo que significaría irrealistamente un 7, o todo bueno, lo que no es verdad pues varias veces me equivoqué a propósito
# el hecho de usar clip demuestra que se está enmascarando un error, probablemente el mismo que da -11 y 11
# Necesito automatizar pruebas 
# para ver como se van ajustando los parámetros de theta y SE
# Ver si lo ejercicios se toman como buenos o no y bajo qué parámetros

# 0.4