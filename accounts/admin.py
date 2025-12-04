from django.contrib import admin

# Register your models here.

from django.core.mail import send_mail
from django.conf import settings
from .models import Docente, Especialidad, Rol

from django.contrib.auth import get_user_model
User = get_user_model()

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email','username','first_name','last_name','is_staff','is_superuser')
    search_fields = ('email','username','first_name','last_name')
        
@admin.action(description="Marcar como verificado y notificar")
def mark_verified(modeladmin, request, queryset):
    for docente in queryset:
        docente.is_verified = True
        docente.save()
        # notificar al docente (opcional)
        try:
            send_mail(
                'Cuenta verificada',
                f'Hola {docente.user.get_full_name()}, tu cuenta ha sido verificada.',
                settings.EMAIL_HOST_USER,
                [docente.user.email],
                fail_silently=True,
            )
        except Exception:
            pass

@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'especialidades')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at','updated_at')
    actions = [mark_verified]
    # mostrar archivo para revisar
    fieldsets = (
        (None, {
            'fields': ('user','biografia','especialidades','is_verified')
        }),
        ('Certificado', {
            'fields': ('certification_file',),
        }),
        ('Tiempos', {
            'fields': ('created_at','updated_at'),
        })
    )

admin.site.register(Especialidad)
admin.site.register(Rol)