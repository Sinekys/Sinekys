# accounts/forms.py
from django import forms
from django.apps import apps
from django.utils.translation import gettext_lazy as _
from django.db import transaction, IntegrityError
import os

from ejercicios.utils.text import normalize_text

# Formulario para estudiantes
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

        # Ajustar requirement de 'career' según el tipo de signup (evita que el formulario
        # para docente falle si por alguna razón se valida con el formulario de estudiante)
        signup_type = None
        try:
            # self.data es un QueryDict en request POST
            signup_type = self.data.get('signup_type') if hasattr(self, 'data') else None
        except Exception:
            signup_type = None

        # Si el signup_type es 'teacher', no requerimos 'career'
        if signup_type == 'teacher':
            self.fields['career'].required = False
        else:
            self.fields['career'].required = True
    
    def signup(self, request, user):
        """
        Método llamado por Allauth después de crear el usuario básico
        """
        Rol = apps.get_model('accounts', 'Rol')
        Estudiante = apps.get_model('accounts', 'Estudiante')
        
        # 1) Guardar datos en el User
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        try:
            # Obtener o crear el rol de estudiante
            rol_est = get_or_create_rol_by_name('Estudiante')
            user.rol = rol_est
            
            with transaction.atomic():
                user.save()
                Estudiante.objects.create(
                    user=user,
                    carrera=self.cleaned_data['career']
                )
        except Exception as e:
            # Intentar eliminar el usuario si falla
            try:
                if user.id:
                    user.delete()
            except Exception:
                pass
            raise forms.ValidationError(_("Error al crear la cuenta de estudiante: ") + str(e))
        
        return user

def get_teacher_signup_form_class():
    """
    Fábrica que devuelve una clase de formulario compatible con allauth
    que incluye los campos estándar de allauth (email, password1, password2)
    y los campos extra para `Docente`. Importamos `SignupForm` dentro
    de la función para evitar importaciones circulares.
    """
    from allauth.account.forms import SignupForm as AllauthSignupForm

    class _TeacherSignupForm(AllauthSignupForm):
        # Campos extra para la versión docente
        first_name = forms.CharField(max_length=30, label=_("Nombre"), required=True)
        last_name = forms.CharField(max_length=30, label=_("Apellido"), required=True)
        especialidades = forms.ModelMultipleChoiceField(
            queryset=None,
            label=_("Especialidades"),
            required=True,
            widget=forms.CheckboxSelectMultiple()
        )
        biography = forms.CharField(label=_("Biografía"), widget=forms.Textarea(attrs={'rows':4}), required=False, max_length=500)
        certification_file = forms.FileField(label=_("Certificado o título"), required=True,
                                            help_text=_("Sube un documento que acredite tu formación como docente (PDF, JPG, PNG - máximo 5MB)"))

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            Especialidad = apps.get_model('accounts', 'Especialidad')
            self.fields['especialidades'].queryset = Especialidad.objects.all()

        def clean_certification_file(self):
            file = self.cleaned_data.get('certification_file')
            if not file:
                raise forms.ValidationError(_("Este campo es obligatorio"))
            # Validar tamaño
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_("El archivo no puede superar los 5 MB"))
            # Validar tipo
            valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(_("Formato de archivo no válido. Solo se permiten PDF, JPG y PNG."))
            return file

        def clean_especialidades(self):
            especialidades = self.cleaned_data.get('especialidades')
            if not especialidades or len(especialidades) == 0:
                raise forms.ValidationError(_("Debes seleccionar al menos una especialidad"))
            return especialidades

        def signup(self, request, user):
            Rol = apps.get_model('accounts', 'Rol')
            Docente = apps.get_model('accounts', 'Docente')

            # Guardar nombres
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            try:
                rol_docente = get_or_create_rol_by_name('Docente')
                user.rol = rol_docente
                with transaction.atomic():
                    user.save()
                    docente = Docente.objects.create(
                        user=user,
                        biografia=self.cleaned_data.get('biography', ''),
                        is_verified=False
                    )
                    especialidades_seleccionadas = self.cleaned_data.get('especialidades')
                    if especialidades_seleccionadas:
                        docente.especialidades.set(especialidades_seleccionadas)
                    cert = self.cleaned_data.get('certification_file')
                    if cert:
                        docente.certification_file.save(cert.name, cert)
                        docente.save()
            except Exception as e:
                try:
                    if hasattr(user, 'docente'):
                        user.docente.delete()
                    if user.id:
                        user.delete()
                except Exception:
                    pass
                raise forms.ValidationError(_("Error al crear la cuenta de docente: ") + str(e))

            return user

    return _TeacherSignupForm


def get_or_create_rol_by_name(nombre):
    """Helper robusto para obtener o crear un Rol evitando errores de secuencia/PK.
    Usa apps.get_model para evitar imports directos y captura IntegrityError si hay
    una condición de carrera o secuencia desincronizada en la base de datos.
    """
    Rol = apps.get_model('accounts', 'Rol')
    rol = Rol.objects.filter(nombre__iexact=nombre).first()
    if rol:
        return rol
    try:
        with transaction.atomic():
            return Rol.objects.create(nombre=nombre)
    except IntegrityError:
        # Otra transacción pudo haber insertado el rol; recuperarlo
        return Rol.objects.filter(nombre__iexact=nombre).first()