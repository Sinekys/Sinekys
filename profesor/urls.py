from django.urls import path
from . import views

app_name = 'profesor'

urlpatterns = [
    path('dashboard/', views.dashboard_profesor, name='dashboard'),
    path('dashboard/data/', views.dashboard_data_json, name='dashboard_data_json'),
]
