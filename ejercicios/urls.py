from django.urls import path
from .views import DiagnosticTestView

urlpatterns = [
    path('diagnostico/', DiagnosticTestView.as_view(), name='diagnostico'),
]