import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_diagnostico_duracion_segundos_and_more'),
        ('ejercicios', '0007_remove_feedback_resumen_ejercicio_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='intento',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddIndex(
            model_name='intento',
            index=models.Index(fields=['uuid'], name='ejercicios__uuid_780af8_idx'),
        ),
    ]