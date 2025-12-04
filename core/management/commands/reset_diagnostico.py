from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import Estudiante, Diagnostico
from ejercicios.models import Intento

User = get_user_model()

class Command(BaseCommand):
    help = 'Reinicia el diagnostico e intentos de un estudiante por ID (acepta student id o user id)'

    def add_arguments(self, parser):
        parser.add_argument('estudiante_id', type=int, help='ID del estudiante (puede ser Estudiante.id o User.id)')

    def handle(self, *args, **options):
        estudiante_id = options['estudiante_id']
        estudiante = None

        # 1) intentar como pk de Estudiante
        try:
            estudiante = Estudiante.objects.get(pk=estudiante_id)
            self.stdout.write(f'Encontrado Estudiante por PK: Estudiante.id={estudiante.id}, user_id={getattr(estudiante, "user_id", None)}')
        except Estudiante.DoesNotExist:
            # 2) intentar como user id (FK)
            estudiante = Estudiante.objects.filter(user__id=estudiante_id).first()
            if estudiante:
                self.stdout.write(f'Encontrado Estudiante por user_id: Estudiante.id={estudiante.id}, user_id={getattr(estudiante, "user_id", None)}')
            else:
                # 3) opcional: comprobar si existe User para dar mensaje más útil
                if User.objects.filter(pk=estudiante_id).exists():
                    self.stdout.write(self.style.ERROR(
                        f'Usuario con ID {estudiante_id} existe, pero no tiene perfil Estudiante asociado.'
                    ))
                else:
                    self.stdout.write(self.style.ERROR(f'Ni Estudiante ni User con ID {estudiante_id} encontrados.'))
                return

        # Borrar dentro de una transacción para seguridad
        with transaction.atomic():
            Intento.objects.filter(estudiante=estudiante).delete()
            Diagnostico.objects.filter(estudiante=estudiante).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Diagnóstico e intentos del Estudiante (Estudiante.id={estudiante.id}, user_id={getattr(estudiante, "user_id", None)}) reiniciados correctamente.'
        ))
#python manage.py reset_diagnostico <estudiante_id>
# comando
#python manage.py reset_diagnostico 2
# reempalzar el 2 con el id que quiero 