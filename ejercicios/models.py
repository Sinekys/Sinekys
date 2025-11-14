from django.db import models
from django.conf import settings
from django.core import validators
from django.utils.translation import gettext_lazy as _
from accounts.models import AbstractBaseModel, Estudiante


class AbstractResultado(models.Model):
    es_correcto = models.BooleanField(verbose_name="¿Es correcto?")
    puntos = models.FloatField(
        verbose_name="Puntos",
        validators=[
            validators.MinValueValidator(0.0),
            validators.MaxValueValidator(1.0)
        ],
        help_text="Valor entre 0 y 1"
    )
    fecha_intento = models.DateTimeField(verbose_name="Fecha del intento")
    class Meta:
        abstract = True
        
    def __str__(self):
        return f"{self.puntos} puntos - {'Correcto' if self.es_correcto else 'Incorrecto'}"
    

class AbstractTiempo(models.Model):
    tiempo_en_segundos = models.FloatField(
        verbose_name="Tiempo en segundos",
        help_text="Tiempo total que tardó el estudiante en resolver el ejercicio"
    )
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return str(self.tiempo_en_segundos)

class TipoEjercicio(models.Model):
    # Elegir entre funciones, matrices,logartimos,multiplicacion...
    TIPO_EJERCICIO_CHOICES = [
    ('funciones', 'Funciones'),
    ('matrices', 'Matrices'),
    ('logaritmos', 'Logaritmos'),
    ('limites', 'Límites'),
]
    tipo_ejercicio = models.CharField(
        max_length=50,
        choices=TIPO_EJERCICIO_CHOICES,
        verbose_name=_("tipo de ejercicio")
    )
    def __str__(self):
        return self.tipo_ejercicio
    

# AbstractBaseModel lleva: created_at, updated_at e is_active
class Ejercicio(AbstractBaseModel):
    # FKs
    materia = models.ForeignKey("core.Materia",verbose_name=_("materia"),on_delete=models.CASCADE)
    unidad = models.ForeignKey("core.Unidad", verbose_name=_("unidad"), on_delete=models.CASCADE)
    docente = models.ForeignKey("accounts.Docente", verbose_name=_("docente"), on_delete=models.SET_NULL, null=True, blank=True)
    tipo_ejercicio = models.ManyToManyField(TipoEjercicio, verbose_name=_("tipo de ejercicio")) 
    
    # Campos
    enunciado = models.CharField(max_length=50,verbose_name=_("enunciado"))
    solucion = models.CharField(max_length=50,verbose_name=_("solucion"))
    dificultad = models.FloatField(db_index=True,
        verbose_name=_("dificultad"),
        validators=[
            validators.MinValueValidator(-3.0),
            validators.MaxValueValidator(3.0)
        ]
    )
    discriminacion = models.FloatField(
        verbose_name=_("discriminación"),
        default=1.0,
        help_text=_("Parámetro a de IRT: mide la pendiente del ítem"),
        validators=[
            validators.MinValueValidator(0.01),   # nunca cero ni negativo
            validators.MaxValueValidator(2.0)     # Será 2 // Al menos eso está en documentaciones que he visto
        ]
    )
    fuente = models.CharField(
        max_length=100,
        choices=[
            ('deepseek', 'DeepSeek'),
            ('llama', 'Llama'),
            ('chatgpt', 'ChatGPT'),
            ('real','Real')
        ],
        verbose_name=_("fuente"),
        help_text=_("De dónde salió el ejercicio"),
        null=True,
        blank=True
    )
    licencia = models.CharField(
        max_length=50,
        choices=[
            ('cc-by', 'CC BY'),
            ('cc-by-sa', 'CC BY-SA'),
            ('cc0', 'CC0'),
            ('mit', 'MIT'),
            ('gpl', 'GPL')
        ],
        null=True,
        blank=True,
        verbose_name='Licencia'
    )
    def __str__(self):
        return self.enunciado
    
class EjercicioVecesMostrado(models.Model):
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE)
    veces_mostrado=models.PositiveBigIntegerField()
    veces_acertado=models.PositiveBigIntegerField()
    
class PasoEjercicio(models.Model):

    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField()
    contenido = models.TextField()
    # olvidé poner el __str__ a este...
    # def __str__(self): # deberé migrar?
    #     return f"Paso {self.orden} - {self.ejercicio.id}"

class Intento(AbstractResultado,AbstractTiempo):
    # FKs
    estudiante = models.ForeignKey("accounts.Estudiante", verbose_name="estudiante", on_delete=models.CASCADE)
    ejercicio = models.ForeignKey(Ejercicio, verbose_name="ejercicio", on_delete=models.CASCADE)
    # Campos
    respuesta_estudiante = models.CharField(max_length=150,verbose_name="respuesta estudiante")
    
    
    def __str__(self):
        return self.respuesta_estudiante
    
class IntentoPaso(models.Model):
    intento = models.ForeignKey(Intento, on_delete=models.CASCADE,related_name='pasos', verbose_name=_('Intento'))
    orden = models.PositiveIntegerField(verbose_name=_('Orden del paso'))
    contenido = models.TextField(verbose_name=_('Contenido del paso'))
    datos_aux = models.JSONField(
        verbose_name=_('Datos auxiliares'),
        help_text=_('Valores o variables intermedias')
    )
    class Meta:
        unique_together = ('intento', 'orden')
        ordering = ['orden']
        verbose_name = _('Paso de Intento')
        verbose_name_plural = _('Pasos de Intento')

    def __str__(self):
        return f"Paso {self.orden} - {self.intento.id}" 

class Feedback(models.Model):
    intento = models.ForeignKey(Intento, verbose_name="feedback", on_delete=models.CASCADE)
    contexto_ejercicio = models.CharField(max_length=512, verbose_name="contexto generado por IA")
    resumen_ejercicio = models.CharField(max_length=512, verbose_name="")
    feedback = models.JSONField(verbose_name="feedback generado por IA")
    fuente_ia = models.CharField(
        max_length=50,
        choices=[
            ('deepseek', 'DeepSeek'),
            ('llama', 'Llama'),
            ('chatgpt', 'ChatGPT'),
        ],
        verbose_name="fuente IA"
    )
    fecha_feedback = models.DateTimeField(auto_now_add=True, verbose_name="fecha del feedback")

    def __str__(self):
        return self.contexto_ejercicio

class TipoFeedback(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="tipo de feedback")
    def __str__(self):
        return self.nombre

class FeedbackPasos(models.Model):
    feedback = models.ForeignKey(Feedback, verbose_name="feedback pasos", on_delete=models.CASCADE)
    tipo_feedback = models.ForeignKey(TipoFeedback, verbose_name="tipo de feedback", on_delete=models.CASCADE)
    # Campos
    
    orden = models.PositiveIntegerField(verbose_name="orden del paso")
    contenido = models.TextField(verbose_name="contenido del paso")
    datos_aux = models.JSONField(
        verbose_name="datos auxiliares",
        help_text="Datos adicionales que pueden ser útiles para el paso, como variables, resultados intermedios, etc."
    )
    
    class Meta:
        unique_together = ('feedback', 'orden')
        ordering = ['orden']
        verbose_name = "Feedback Paso"
        verbose_name_plural = "Feedback Pasos"
        
    def __str__(self):
        return f"{self.feedback.id} + {self.orden} + {self.tipo_feedback.nombre} + {self.contenido[:50]}"
    
    
    
    
#   -----------------------  GRUPOS -----------------------  # 
#   -----------------------  GRUPOS -----------------------  # 
#   -----------------------  GRUPOS -----------------------  #


class GruposEstudio(AbstractBaseModel):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del grupo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del grupo")
    materia = models.ForeignKey("core.Materia", verbose_name="Materia del grupo", on_delete=models.CASCADE)
    docente = models.ForeignKey("accounts.Docente", verbose_name="Docente del grupo", on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self): 
        return self.nombre
    
class MiembrosGrupo(models.Model):
    estudiante = models.ForeignKey(Estudiante, verbose_name="id_estudiante", on_delete=models.CASCADE)
    grupo = models.ForeignKey(GruposEstudio, verbose_name="id_grupo", on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('estudiante', 'grupo')
        verbose_name = "Miembro del Grupo"
        verbose_name_plural = "Miembros del Grupo"
    
    def __str__(self):
        return f'{self.estudiante} + {self.grupo}'

class IntentoGrupal(AbstractResultado, AbstractTiempo):
    grupo = models.ForeignKey(GruposEstudio, verbose_name="id_grupo", on_delete=models.CASCADE)
    ejercicio = models.ForeignKey(Ejercicio, verbose_name="id_ejercicio", on_delete=models.CASCADE)
    # campos
    respuesta_final = models.CharField(verbose_name="respuesta final del ejercicio") 
    
    class Meta: 
        unique_together = ('grupo', 'ejercicio')
        verbose_name = "Intento Grupal"
        verbose_name_plural = "Intentos Grupales"
    
    def __str__(self):
        return f'{self.grupo} + {self.ejercicio} + {self.respuesta_final}'

class RespuestaIndividual(AbstractTiempo):
    intento_grupal = models.ForeignKey(IntentoGrupal, verbose_name="intento_grupal", on_delete=models.CASCADE)
    estudiante = models.ForeignKey(Estudiante, verbose_name="estudiante", on_delete=models.CASCADE)
    # campos
    respuesta = models.CharField(max_length=150, verbose_name="respuesta_estudiante_grupo")

    class Meta:
        unique_together = ('estudiante', 'intento_grupal')


    
    def __str__(self):
        return f'{self.intento_grupal} + {self.estudiante} + {self.respuesta}'
    