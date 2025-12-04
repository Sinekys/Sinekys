# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Docente
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Docente)
def notify_admin_new_teacher(sender, instance, created, **kwargs):
    if created:
        # Obtener especialidades como texto
        especialidades = ", ".join([e.nombre for e in instance.especialidades.all()])
        
        subject = 'Nuevo docente registrado - Requiere verificación'
        message = f"""
Se ha registrado un nuevo docente que requiere verificación:

Nombre: {instance.user.get_full_name()}
Email: {instance.user.email}
Especialidades: {especialidades}

Por favor, revisa y verifica su cuenta en el panel de administración.
        """
        from_email = settings.EMAIL_HOST_USER
        admin_email = settings.ADMIN_EMAIL
        
        try:
            send_mail(
                subject,
                message,
                from_email,
                [admin_email],
                fail_silently=False,
            )
            logger.info(f"Notificación enviada al administrador para el docente {instance.user.email}")
        except Exception as e:
            logger.error(f"Error al enviar notificación para el docente {instance.user.email}: {str(e)}")