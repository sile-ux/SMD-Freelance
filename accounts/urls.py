from django.urls import path
from . import views

urlpatterns = [
    path('inscription/', views.choice_register, name='choice_register'),
    path('inscription/freelance/', views.register_freelance, name='register_freelance'),
    path('inscription/client/', views.register_client, name='register_client'),
    path('connexion/', views.user_login, name='login'),
    path('deconnexion/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]