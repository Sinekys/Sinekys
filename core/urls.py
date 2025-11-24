from django.urls import path
from .views import home_view, index_view, about, goals, how_does_it_work

urlpatterns = [
    path('', index_view, name='index'),
    path('inicio/', home_view, name='mainPage'),
    path('about/', about, name='about'),
    path('objetivos/', goals, name='goals'),
    path('comoFunciona/', how_does_it_work, name='how_does_it_work'),
]
