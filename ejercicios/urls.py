from django.urls import path,register_converter
from .views import DiagnosticTestView,EjercicioView,MatchMakingGroupView, CheckAnswer
from . import converters


register_converter(converters.UUIDConverter, 'uuid')

urlpatterns = [
    path('diagnostico/', DiagnosticTestView.as_view(), name='diagnostico'),
    path('', EjercicioView.as_view(), name='ejercicio'),                      
    path('<int:ejercicio_id>/', EjercicioView.as_view(), name='ejercicio_detalle'), 
    path('check/<uuid:intento_uuid>/', CheckAnswer.as_view(), name='check-respuesta'),
    path('matchmaking-grupo/', MatchMakingGroupView.as_view(), name='matchmakingGroup'),
]