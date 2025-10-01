import numpy as np
from scipy.optimize import minimize
from django.db import transaction
from accounts.models import Diagnostico
from .models import Intento, Ejercicio

# Scipy sirve para algoritmos de optimización, integración
# estadística, álgebra lineal, entre otras cosas
# ayuda a encontrar máximos y minimos de funciones
# incluye herramientas para realizar análisis estadísticos y trabajar con procesos aleatorios
def actualizar_diagnostico(estudiante):
    # Obejtivo: Estimar theta usando 2PL e intentos del estudiante
    # Actualizar y/o crear el objeto Diagnostico  
    intentos = Intento.objects.filter(estudiante=estudiante).select_related('ejercicio')
    
    if not intentos:
        return None
    
    datos = []
    for intento in intentos:
        item = intento.ejercicio
        b = item.dificultad
        a = item.discriminacion or 1.0
        # Todavía necesito conocer si esto es lo mejor, aunque no creo...
        correcto = 1 if intento.es_correcto else 0
        datos.append((correcto,a,b))
        
    # función de verosimilitud (tengo que estudiar esta parte)
    def verosimilitud(theta):
        # Logarítmico
        verosimilitud = 0.0
        
        for correcto,a ,b in datos:
            exponente = -a*(theta-b)
            # evitar overflow
            if exponente > 50:
                prob = 0.0
            elif exponente < -50:
                prob = 1.0
            else:
                prob = 1/(1+np.exp(exponente))
                
        # Aegurarme que la probabilidad no sea ni 0 ni 1
        prob = max(1e-12, min(prob, 1 - 1e-12))
        
        if correcto:
            verosimilitud += np.log(prob)
        else:
            verosimilitud += np.log(1-prob)
        
        return -verosimilitud #negativo par aque minimize busque el minimo | minimize es funció nde scipy
    
    try:
        result = minimize(verosimilitud, x0=0.0,method='BFGS') #????
        theta_estimado = float(result.x[0])
        
        # Calcular Error Estándar: 1 / sqrt(información total)
        info_total = -result.hess_inv  # Aproximación de la matriz de información || Y esto? No debería estar usando matrices hessianas aquí...
        if hasattr(info_total, 'diagonal'):
            varianza = 1.0 / info_total.diagonal()[0]
        else:
            varianza = 1.0 / (-result.hess_inv) if result.hess_inv < 0 else 1.0
        #SE : Standard Error 
        se = np.sqrt(varianza) if varianza > 0 else 1.0
        
    except Exception:
        theta_estimado = 0.0 #fallback
        se = 1.0
    
    
    #guardar
    with transaction.atomic():
        Diagnostico.objects.update_or_create(
            estudiante=estudiante,
            defaults={'theta': theta_estimado,
                      "error_estimacion": se}
        )
    return theta_estimado, se
    # pass

# Reflexión: Esto podría ser considerado machine learning

def seleccionar_siguiente_ejercicio(estudiante):
    # Objetivo: seleccionar el ítem con máxima informacion
    # Método Fisher?
    # theta
    try:
        theta = estudiante.diagnostico.theta
    except:
        theta = 0.0
        
    # evitar que se repitan items
    intentos_previos = Intento.objects.filter(estudiante=estudiante)
    ids_respondidos = intentos_previos.values_list('ejercicio_id', flat=True)
    
    disponibles = Ejercicio.objects.exclude(id__in=ids_respondidos)
    
    mejor_item = None
    max_info = -1
    for item in disponibles:
        b = item.dificultad
        a = item.discriminacion or 1.0
        
        # Probalidad de acierto usando 2PL
        z = a * (theta -b )
        
        # clipping para evitar overflow | qué es esto y por qué es útil??
        z = np.clip(z, -50,50)
        prob = 1/(1+np.exp(-z))
        
        # información del ítem
        info = a**2 * prob * (1-prob)
        
        if info > max_info:
            max_info = info
            mejor_item = item
    if not mejor_item:
        mejor_item = Ejercicio.objects.order_by('?').first()
    
    return mejor_item 