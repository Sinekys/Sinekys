import unicodedata
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Carrera(models.Model):
    nombre = models.CharField(max_length=100, verbose_name=_("Carrera"), db_index=True)
    semestres = models.IntegerField(verbose_name=_("Semestres"), null= True, blank=True) 
    descripcion = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))
    
    def save(self, *args, **kwargs):
        # Corregir codificación al guardar
        if self.nombre:
            self.nombre = unicodedata.normalize('NFKC', self.nombre.strip())
        super().save(*args, **kwargs)
    def __str__(self):
        return unicodedata.normalize('NFKC', self.nombre)
    
class Materia(models.Model):
    nombre = models.CharField(max_length=100, verbose_name=_("Materia Name"))
    descripcion = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    carreras = models.ManyToManyField(Carrera,through='CarreraMateria',related_name='materias',verbose_name='Carreras')
    class Meta:
        verbose_name = _("Materia")
        verbose_name_plural = _("Materias")

    def __str__(self):
        return self.nombre

class Unidad(models.Model):
    materia = models.ForeignKey(Materia, related_name='unidades', on_delete=models.CASCADE, verbose_name=_("Materia"))
    num_unidad = models.IntegerField()
    nombre = models.CharField(max_length=100, verbose_name=_("Unidad Name"))
    objetivo = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Unidad")
        verbose_name_plural = _("Unidades")
    
    def __str__(self):
        return self.nombre

class CarreraMateria(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, verbose_name='Carrera')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, verbose_name='Materia')
    semestre = models.PositiveSmallIntegerField(_("Semestre"))
    
    class Meta:
        verbose_name = _("Carrera-Materia")
        verbose_name_plural = _("Carreras-Materias")
        unique_together = ('carrera', 'materia')
    
    def __str__(self):
        return f"{self.carrera.nombre} - {self.materia.nombre} - (Sem {self.semestre})"
class Seccion(models.Model):
    nombre = models.CharField(max_length=50, verbose_name='Nombre de la sección')
    jornada = models.CharField(verbose_name="jornada de la materia",
                               choices=[('diurna','Diurna'),
                                        ('vespertina','Vespertina')])
    def __str__(self):
        return self.nombre

class DocenteMateria(models.Model):
    docente = models.ForeignKey(
        'accounts.Docente',
        on_delete=models.CASCADE,
        related_name='materias_asignadas',
        verbose_name='Docente'
    )
    materia = models.ForeignKey(
        'core.Materia',
        on_delete=models.CASCADE,
        related_name='docentes_asignados',
        verbose_name='Materia'
    )
    seccion = models.ForeignKey('core.Seccion', on_delete=models.PROTECT)
    fecha_inicio = models.DateField(verbose_name='Fecha inicio')
    fecha_fin = models.DateField(null=True, blank=True, verbose_name='Fecha fin')

    class Meta:
        unique_together = ('docente', 'materia', 'seccion', 'fecha_inicio')
        verbose_name = 'Docente-Materia'
        verbose_name_plural = 'Docentes-Materias'

    def clean(self):
        if self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio.")

    def __str__(self):
        return f"{self.docente.user.get_full_name()} -> {self.materia.nombre}"

