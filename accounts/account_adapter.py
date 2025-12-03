from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

class MyAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        user = request.user
        
        # Si el usuario tiene rol
        if hasattr(user, "rol_id") and user.rol_id:
            # Valor que usas para distinguir roles
            if user.rol_id == 1:   # por ejemplo: 1 = docente
                return "/profesor/dashboard/"
            elif user.rol_id == 2:  # 2 = alumno
                return "/inicio/"
        
        # Si no tiene rol, redirigir por defecto
        return "/"
