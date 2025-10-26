from django.urls import path
from .views import DiagnosticTestView,EjercicioView,MatchMakingGroupView

urlpatterns = [
    path('diagnostico/', DiagnosticTestView.as_view(), name='diagnostico'),
    path('ejercicio/', EjercicioView.as_view(), name='ejercicio'),
    path('matchmaking-grupo/', MatchMakingGroupView.as_view(), name='matchmakingGroup'),
]