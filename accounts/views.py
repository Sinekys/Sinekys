# accounts/views.py
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from allauth.account.views import SignupView
from .forms import CustomSignupForm, get_teacher_signup_form_class
from django.contrib.auth.decorators import login_required
class StudentSignupView(SignupView):
    template_name = "account/signup.html"
    form_class = CustomSignupForm
    success_url = reverse_lazy('account_email_verification_sent')

class TeacherSignupView(SignupView):
    template_name = "account/teacher_signup.html"
    success_url = reverse_lazy('docente_esperar_validacion')

    def get_form_class(self):
        # Devolver la clase de formulario ligada a allauth dinámicamente
        return get_teacher_signup_form_class()

def docente_esperar_validacion(request):
    """Vista para mostrar el mensaje de esperar validación después de registrarse como docente"""
    return render(request, 'docente/esperar_validacion.html')

@login_required
def profile(request):
    return render(request, 'account/profile.html')

@login_required
def progress(request):
    return render(request, 'account/progress.html')