import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ejercicios', '0005_alter_ejercicio_enunciado'),
    ]

    operations = [
        migrations.CreateModel(
            name='EjercicioVecesMostrado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('veces_mostrado', models.PositiveBigIntegerField()),
                ('veces_acertado', models.PositiveBigIntegerField()),
                ('ejercicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ejercicios.ejercicio')),
            ],
        ),
    ]