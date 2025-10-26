"""
URL configuration for sinekys project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
# from accounts import urls as accounts_urls
from core import urls as core_urls
from ejercicios import urls as ejercicios_urls
from django.conf import settings
from django.conf.urls.static import static 
from core.views import home_view
urlpatterns = [
    path('admin/', admin.site.urls),

    # path('', home_view, name='mainPage'),
    path('', include(core_urls)),
    # path('loggin/', include(accounts_urls)),
    path('accounts/', include('allauth.urls')),
    
    path('ejercicios/', include(ejercicios_urls)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
