from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core import validators
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
# from datetime import timezone
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)
    
class CustomUser(AbstractUser):
    username = models.CharField(
        _('Nombre de usuario'),
        max_length=50,
        unique=True,
        help_text=_('Requerido. 50 caracteres o menos. Letras, números y @/./+/-/_ solamente.'),
        validators=[
            validators.RegexValidator(
                r'^[\w.@+-]+$',
                _('Ingrese un nombre de usuario válido. Este valor solo puede contener letras, números y @/./+/-/_ caracteres.'),
                'invalid'
            ),
        ],
        error_messages={
            'unique': _("Ya existe un usuario con este nombre de usuario."),
        },
        
    )
    
    email = models.EmailField(_('Correo electrónico'), unique=True)
    first_name = models.CharField(_('nombre'), max_length=150)
    last_name = models.CharField(_('apellido'), max_length=150)
    is_vip = models.BooleanField(default=False, verbose_name='VIP')
    rol = models.ForeignKey('Rol', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Rol")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username','first_name','last_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

# Base Abstractions
class AbstractBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} (ID: {self.pk})"

# Rol
class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Rol')

    def __str__(self):
        return self.nombre

# Estudiante
class Estudiante(AbstractBaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='estudiante')
    carrera = models.ForeignKey("core.Carrera", verbose_name=_("Carrera"), on_delete=models.CASCADE)
    semestre_actual = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=1,
        verbose_name="Semestre actual",
        help_text="Semestre en el que está inscrito el estudiante")
    def __str__(self):
        return f"Estudiante: {self.user.get_full_name()}"

class Diagnostico(models.Model):
    estudiante = models.OneToOneField('Estudiante', on_delete=models.CASCADE, verbose_name='Estudiante')
    theta = models.FloatField(validators=[MinValueValidator(-3), MaxValueValidator(3)])
    error_estimacion = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        verbose_name="Error estándar de estimación",
        help_text="Precisión de la estimación de theta (SE). Valores bajos = alta precisión."
    )
    fecha = models.DateTimeField(auto_now_add=True)
    # === Nuevos campos para gestionar el flujo ===
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.PositiveIntegerField(default=3540)  # 59 minutos
    finalizado = models.BooleanField(default=False)
    
    def tiempo_restante(self):
        if not self.fecha_inicio:
            return self.duracion_segundos
        transcurrido = (timezone.now() - self.fecha_inicio).total_seconds()
        return max(0, self.duracion_segundos - transcurrido)

    def is_expired(self):
        return self.tiempo_restante() <= 0

    def save(self, *args, **kwargs):
    # Establecer fecha_inicio la primera vez que se guarda con finalizado=False y sin fecha_inicio
        if self.fecha_inicio is None and not self.finalizado:
            self.fecha_inicio = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Diagnóstico de {self.estudiante.user.get_full_name()}'
    
    
class ProgresoMateria(models.Model):
    estudiante  = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name='progresos')
    materia     = models.ForeignKey('core.Materia', on_delete=models.PROTECT)
    fecha_inicio   = models.DateField(auto_now_add=True)
    fecha_finalizacion = models.DateField(null=True, blank=True)
    estado_choices  = [
        ('pendiente', 'Pendiente'),
        ('en_curso', 'En curso'),
        ('aprobada', 'Aprobada'),
        ('reprobada', 'Reprobada'),
    ]
    estado = models.CharField(max_length=10, choices=estado_choices, default='pendiente')

    class Meta:
        unique_together = ('estudiante', 'materia')


# Docente
class Especialidad(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Especialidad')

    def __str__(self):
        return self.nombre

class Docente(AbstractBaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='docente')
    especialidad = models.ForeignKey(Especialidad, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Especialidad')
    biografia = models.TextField(max_length=500, blank=True, verbose_name='Biografía')
    materias = models.ManyToManyField("core.Materia", through='core.DocenteMateria', verbose_name='Materias')

    def __str__(self):
        return f"Docente: {self.user.get_full_name()}"


class Payment(models.Model):
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, verbose_name='Estudiante')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto')
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de pago')
    method = models.CharField(max_length=50, verbose_name='Método de pago')
    def __str__(self):
        return f'Pago de {self.estudiante.user.get_full_name()} - {self.amount} - {self.payment_date}'