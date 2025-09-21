# ejercicios/views.py
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from ejercicios.models import Ejercicio
from accounts.models import CustomUser
from django.db.models import F
# API ChatGPT
from request import contextualize_exercise




@method_decorator(login_required, name='dispatch') #Verifica si está loggeado
class DiagnosticTestView(View):
    def get(self, request):
        # Buscar un ejercicio con dificultad = b
        # Podría tomar el nivel del estudiante como dificultad no? Momento, eso solo serviría cuando el nivel del estudiante ya fue determinado
        # Por lo que lo necesario ahora es fijar una dificultad promedio, lo que significa que "b" será una variable fija
        # que luego sera ajustada segun las respuestas que vaya otorgando
        # Hay tan solo 1 problema, no hubo un estudio/metodología detrás para determinar la dificultad de los ejercicios (al menos no documentada)
        # fue a la pinta del jean, lo que no está mal, despues de todo es necesario un nivel y luego se vaya ajustando gracias al algoritmo
        # dificultad
        b = 0.05 #Podría aprovechas que el jean puso la dificultad de los ejercicios muy cercana a 0 ( 0,04 por ej) para 
        # modificar el limite de las tablas y hacerlo según la documentación de IRT (oscila entre -3 y +3) #PENDIENTE PENDIENTE PENDIENTE PENDIENTE PENDIENTE
        ejercicio = Ejercicio.objects.filter(dificultad__gte=b).order_by('dificultad').first() #está buscando el primer resultado similar a la dificultad establecida
        # Quizás nos sea la mejor manera, uno aleatorio puede ser mejor

        carrera = ejercicio.materia.carreras.first().nombre if ejercicio.materia.carreras.exists() else "General"

        # LLM contextualización
        contexto = contextualize_exercise(ejercicio, carrera)

        context = {
            "ejercicio": ejercicio,
            "contexto": contexto, #respuesta # por ahora son muy básicas
        }
        return render(request, "diagnostico/index.html", context)
    def post(self):
        # necesito obtener los pasos y la respuesta del estudiante
        # 
