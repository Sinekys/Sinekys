import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_remove_diagnostico_puntaje_irt_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='diagnostico',
            name='error_estimacion',
            field=models.FloatField(blank=True, help_text='Precisión de la estimación de theta (SE). Valores bajos = alta precisión.', null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(2.0)], verbose_name='Error estándar de estimación'),
        ),
    ]