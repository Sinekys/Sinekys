import numpy as np
from scipy.optimize import minimize
from django.db import transaction
from accounts.models import Diagnostico
from .models import Intento, Ejercicio
import numpy as np
def actualizar_diagnostico(estudiante):
    # Obejtivo: Estimar theta usando Rasch (1PL)
    # Actualizar y/o crear el objeto Diagnostico  
    intentos = Intento.objects.filter(estudiante=estudiante).select_related('ejercicio')
    if not intentos:
        return 0.0, 1.0 #Theta inicial neutro, SE alto
    
    datos = []
    for intento in intentos:
        item = intento.ejercicio
        b = item.dificultad
        #a = item.discriminacion or 1.0 #Si no estoy mal, debería ser 1.0 si bien es de 1 en todos, no sé como influiría en los algoritmos aplicar la misma discriminación para cada item, supongo que esta mal 
                                       # Ya que no todos deberían discriminar por igual, pero qué tanto influye usar la formula de 2PL con a=1 como constante?
        correcto = 1 if intento.es_correcto else 0
        datos.append((correcto,b))
        
    # función de verosimilitud (tengo que estudiar esta parte)
    def log_verosimilitud(theta_array):
        # Logarítmico
        theta = theta_array[0]
        theta = np.clip(theta,-3.0,3.0) # evitar overflow
        verosimilitud = 0.0
        
        for correcto,b in datos:
            z = theta - b #Exponente
            z = np.clip(z,-50,50)
            prob = 1/(1+np.exp(-z))
            prob = np.clip(prob, 1e-12, 1-1e-12)
            verosimilitud += np.log(prob) if correcto else np.log(1-prob) #
        return verosimilitud
        # Asegurarme que la probabilidad no sea ni 0 ni 1
        # prob = max(1e-12, min(prob, 1 - 1e-12))
    try:
        from scipy.optimize import Bounds 
        bounds = Bounds([-3.0],[3.0])
        result = minimize(
            log_verosimilitud,
            x0=[0.0],
            method='L-BFGS-B',
            bounds=bounds
        )
        theta_estimado = float(np.clip(result.x[0], -3.0,3.0))
        
        # Calcular SE suando infor de Fisher para 1PL
        info_total = 0.0
        for correcto,b in datos:
            z= theta_estimado - b
            z = np.clip(z,-50,50)
            prob = 1/(1+np.exp(-z))
            info_total += prob * (1-prob) #a=1 -> I(theta) = P(1-P)
        se = 1.0 / np.sqrt(info_total) if info_total > 0 else 1.0
        se = np.clip(se, 0.2,2.0)
    
    except Exception:
        theta_estimado = 0.0 #Fallback
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


# En 1pl, la informació nde Fisher de un ítem es
    # Ii(theta) = Pi(theta) * [1- Pi(theta)]
    # Pi = P sub i / no 3.14 no tiene nada que ver la constante pi

def seleccionar_siguiente_ejercicio(estudiante):
    # Objetivo: seleccionar el ítem con máxima informacion
    # Método Fisher?
    # theta
    theta = 0.0 #Se supone que el usuario no ha hecho ningún ejercicio antes, por lo que su nivel debería ser 0
        
    try:
        if hasattr(estudiante, 'diagnostico') and estudiante.diagnostico:
            theta = estudiante.diagnostico.theta
    except Diagnostico.DoesNotExist:
        pass
        
    # evitar que se repitan items
    intentos_previos = Intento.objects.filter(estudiante=estudiante)
    ids_respondidos = intentos_previos.values_list('ejercicio_id', flat=True)

    disponibles = Ejercicio.objects.exclude(id__in=ids_respondidos)
    
    mejor_item = None
    max_info = -1
    for item in disponibles:
        b = item.dificultad
        # a = item.discriminacion or 1.0
        
        
        z =  theta -b 
        
        # clipping para evitar overflow | qué es esto y por qué es útil?? ya sé pero lo debo definir
        z = np.clip(z, -50,50)
        prob = 1/(1+np.exp(-z))
        
        # información del ítem
        info = prob * (1-prob)
        
        if info > max_info:
            max_info = info
            mejor_item = item
    if not mejor_item:
        mejor_item = Ejercicio.objects.order_by('?').first()
    
    return mejor_item  

# Veo que hay mucho código repetible, sobre todo z y prob