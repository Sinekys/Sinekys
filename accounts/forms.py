# accounts/forms.py

from django import forms
from django.apps import apps
from django.utils.translation import gettext_lazy as _
from ejercicios.utils.text import normalize_text

class CustomSignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=30, 
        label=_("Nombre"), 
        required=True
    )
    last_name = forms.CharField(
        max_length=30, 
        label=_("Apellido"), 
        required=True
    )
    career = forms.ModelChoiceField(
        queryset=None, 
        label=_("Carrera"), 
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Carrera = apps.get_model('core', 'Carrera')
        self.fields['career'].queryset = Carrera.objects.all()
        
        self.fields['career'].choices = [
            (c.id, normalize_text(c.nombre)) for c in Carrera.objects.all()
        ]

    def signup(self, request, user):
        # 1) Guardar datos en el User
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.save()

        # 2) Crear perfil Estudiante
        Estudiante = apps.get_model('accounts', 'Estudiante')
        Estudiante.objects.create(
            user=user,
            carrera=self.cleaned_data['career']
        )
        return user
