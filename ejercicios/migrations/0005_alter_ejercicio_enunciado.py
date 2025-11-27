from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ejercicios', '0004_ejercicio_discriminacion_alter_ejercicio_dificultad'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ejercicio',
            name='enunciado',
            field=models.CharField(max_length=50, verbose_name='enunciado'),
        ),
    ]