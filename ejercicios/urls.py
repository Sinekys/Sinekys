from django.urls import path
from .views import DiagnosticTestView,EjercicioView,MatchMakingGroupView, CheckAnswer

urlpatterns = [
    path('diagnostico/', DiagnosticTestView.as_view(), name='diagnostico'),
    path('', EjercicioView.as_view(), name='ejercicio'),                      
    path('<int:ejercicio_id>/', EjercicioView.as_view(), name='ejercicio_detalle'), 
    path('check/<int:intento_id>/', CheckAnswer.as_view(), name='check-respuesta'),
    path('matchmaking-grupo/', MatchMakingGroupView.as_view(), name='matchmakingGroup'),
]