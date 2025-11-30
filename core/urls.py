from django.urls import path
from .views import home_view, index_view, about, goals, how_does_it_work, pricing, terminos, privacidad, ayuda, ejercicio_grupal_view,dashboard

urlpatterns = [
    path('', index_view, name='index'),
    path('inicio/', home_view, name='mainPage'),
    path('about/', about, name='about'),
    path('objetivos/', goals, name='goals'),
    path('comoFunciona/', how_does_it_work, name='how_does_it_work'),
    path('pricing/', pricing, name='pricing'),
    # 🚨 RUTAS LEGALES FALTANTES
    path('terminos/', terminos, name='terminos'),
    path('privacidad/', privacidad, name='privacidad'),
    path('ayuda/', ayuda, name='ayuda'),
    path('ejercicioGrupal/', ejercicio_grupal_view, name='ejercicio_grupal'),
    path('dashboard/', dashboard, name='dashboard'),

]
