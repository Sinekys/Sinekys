import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ejercicios', '0003_ejercicio_licencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='ejercicio',
            name='discriminacion',
            field=models.FloatField(default=1.0, help_text='Parámetro a de IRT: mide la pendiente del ítem', validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.MaxValueValidator(2.0)], verbose_name='discriminación'),
        ),
        migrations.AlterField(
            model_name='ejercicio',
            name='dificultad',
            field=models.FloatField(db_index=True, validators=[django.core.validators.MinValueValidator(-3.0), django.core.validators.MaxValueValidator(3.0)], verbose_name='dificultad'),
        ),
    ]