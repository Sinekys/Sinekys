from django.urls import path
from . import views

app_name = 'profesor'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_profesor, name='dashboard'),
    
    # Carga masiva de ejercicios
    path('dashboard/upload/', views.upload_ejercicios_view, name='upload_ejercicios'),
    path('ejercicios/plantilla/', views.descargar_plantilla_view, name='descargar_plantilla'),
    
    # API para obtener unidades por materia
    path('api/unidades/', views.get_unidades_por_materia, name='get_unidades'),
]