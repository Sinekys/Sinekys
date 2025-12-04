# accounts/urls.py
from django.urls import path
from .views import StudentSignupView, TeacherSignupView, docente_esperar_validacion

urlpatterns = [
    path('signup/', StudentSignupView.as_view(), name='account_signup'),
    path('signup/docente/', TeacherSignupView.as_view(), name='teacher_signup'),
    path('docente/esperar-validacion/', docente_esperar_validacion, name='docente_esperar_validacion'),
]