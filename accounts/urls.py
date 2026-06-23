app_name = 'accounts'
from django.urls import path
from . import views
from .views import home_view, choice_register, register_client, freelance_register_view, user_login, user_logout, \
    dashboard, transaction_view, parametre_view

urlpatterns = [


    # 🏠 LA ROUTE ACCUEIL (Accessible via http://127.0.0.1:8000/home)
    path('home', home_view, name='home'),

    # Facultatif : Si tu veux que l'adresse racine (http://127.0.0.1:8000/) mène aussi à l'accueil
    path('', home_view, name='index'),

    # Tes autres routes d'authentification existantes
    path('accounts/choice/', choice_register, name='choice_register'),
    path('accounts/register/client/', register_client, name='register_client'),
    path('accounts/register/freelance/', freelance_register_view, name='register_freelance'),
    path('accounts/login/', user_login, name='login'),
    path('accounts/logout/', user_logout, name='logout'),
    path('accounts/dashboard/', dashboard, name='dashboard'),
    path('inscription/', views.choice_register, name='choice_register'),
    path('register/freelance/', views.freelance_register_view, name='register_freelance'),
    path('inscription/client/', views.register_client, name='register_client'),
    path('connexion/', views.user_login, name='login'),
    path('deconnexion/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transaction/', views.transaction_view, name='transaction'),
    path('parametre/', views.parametre_view, name='parametre'),
    path('inscription-freelance/', views.freelance_register_view, name='freelance_register_view'),
]

