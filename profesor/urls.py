from django.urls import path
from . import views

app_name = 'profesor'

urlpatterns = [
    path('dashboard/', views.dashboard_profesor, name='dashboard'),

]
