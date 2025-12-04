import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_customuser_username'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='diagnostico',
            name='puntaje_irt',
        ),
        migrations.AlterField(
            model_name='diagnostico',
            name='theta',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(-3), django.core.validators.MaxValueValidator(3)]),
        ),
    ]