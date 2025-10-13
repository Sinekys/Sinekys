from django.core.management.base import BaseCommand
from accounts.models import Diagnostico, Estudiante
from ejercicios.models import Intento

class Command(BaseCommand):
    help =' Reinicia el diagnostico e intentos de un estudiante por ID'
    def add_arguments(self, parser):
        parser.add_argument('estudiante_id', type=int,help='ID del estudiante')
    
    def handle(self, *args, **options):
        estudiante_id = options['estudiante_id']
        try:
            estudiante = Estudiante.objects.get(pk=estudiante_id)
        except Estudiante.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Estudiante con ID {estudiante_id} no encontrado')
            )
            return
        
        Intento.objects.filter(estudiante=estudiante).delete()
        Diagnostico.objects.filter(estudiante=estudiante).delete()
        self.stdout.write(
            self.style.SUCCESS(f'Diagnóstico e intentos de estudiante con ID: {estudiante_id} reiniciados correctamente')
        )
# comando
#python manage.py reset_diagnostico 2
# reempalzar el 2 con el id que quiero 