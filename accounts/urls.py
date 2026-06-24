app_name = 'accounts'
from django.urls import path
from . import views

urlpatterns = [

    path('home', views.home_view, name='home'),

    path('', views.home_view, name='index'),

    path('accounts/choice/', views.choice_register, name='choice_register'),
    path('accounts/register/client/', views.register_client, name='register_client'),
    path('accounts/register/freelance/', views.freelance_register_view, name='register_freelance'),
    path('accounts/login/', views.user_login, name='login'),
    path('accounts/logout/', views.user_logout, name='logout'),
    path('accounts/dashboard/', views.dashboard, name='dashboard'),
    path('inscription/', views.choice_register, name='choice_register'),
    path('register/freelance/', views.freelance_register_view, name='register_freelance'),
    path('inscription/client/', views.register_client, name='register_client'),
    path('connexion/', views.user_login, name='login'),
    path('deconnexion/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transaction/', views.transaction_view, name='transaction'),
    path('parametre/', views.parametre_view, name='parametre'),
    path('inscription-freelance/', views.freelance_register_view, name='freelance_register_view'),
    path('freelances/', views.freelance_list_view, name='freelance_list'),
    path('statistiques/', views.stat_freelancer_view, name='stat_freelancer'),
]

