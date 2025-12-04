# accounts/adapter.py
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse

class CustomAccountAdapter(DefaultAccountAdapter):
    
    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            if hasattr(request.user, 'docente') and not request.user.docente.is_verified:
                return settings.TEACHER_PENDING_VERIFICATION_URL
        return super().get_login_redirect_url(request)
    
    def save_user(self, request, user, form, commit=True):
        """
        Este método es llamado por Allauth para guardar el usuario
        Es donde debemos personalizar los campos adicionales
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Guardar los campos personalizados (first_name, last_name)
        if hasattr(form, 'cleaned_data'):
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
        
        if commit:
            user.save()
        
        return user