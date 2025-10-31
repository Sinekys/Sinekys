from django.urls import path
from .views import DiagnosticTestView,EjercicioView,MatchMakingGroupView, CheckAnswer

urlpatterns = [
    path('diagnostico/', DiagnosticTestView.as_view(), name='diagnostico'),
    path('ejercicio/<int:ejercicio_id>', EjercicioView.as_view(), name='ejercicio'),
    path('ejercicio/check/<int:ejercicio_id>', CheckAnswer.as_view(), name='check-respuesta'),
    # path('matchmaking-grupo/', MatchMakingGroupView.as_view(), name='matchmakingGroup'),
]