# accounts/views.py
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from allauth.account.views import SignupView
from .forms import CustomSignupForm, get_teacher_signup_form_class
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count
from ejercicios.models import Intento
from accounts.models import Estudiante

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

class TeacherDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "docente/main_page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        docente = getattr(self.request.user, 'docente', None)
        if not docente:
            return ctx
        materias = docente.materias.all()
        # Recent attempts on my materias
        recent_attempts = Intento.objects.filter(
            ejercicio__materia__in=materias
        ).select_related('estudiante__user','ejercicio').order_by('-fecha_intento')[:10]

        # Students per materia
        students_by_materia = (Estudiante.objects.filter(progresos__materia__in=materias)
                               .values('progresos__materia__id','progresos__materia__nombre')
                               .annotate(n_students=Count('id', distinct=True)))

        ctx.update({
            'docente': docente,
            'materias': materias,
            'recent_attempts': recent_attempts,
            'students_by_materia': students_by_materia,
            'is_verified': docente.is_verified,
        })
        return ctx