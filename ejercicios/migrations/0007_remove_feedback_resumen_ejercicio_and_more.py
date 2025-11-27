from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ejercicios', '0006_ejerciciovecesmostrado'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='feedback',
            name='resumen_ejercicio',
        ),
        migrations.AlterField(
            model_name='feedback',
            name='contexto_ejercicio',
            field=models.TextField(blank=True, help_text='Explicación/Solución/COntexto generado por IA para este intento', null=True, verbose_name='contexto generado por IA'),
        ),
    ]