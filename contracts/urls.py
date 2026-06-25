# contracts/urls.py
from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    # Les 3 routes backend pour tes pages
    path('freelances/api/', views.freelance_list_api, name='freelance_list'),
    path('disponibles/api/', views.mission_list_api, name='mission_list'),
    path('tarifs/api/', views.tarifs_api, name='tarifs'),
    path('contract/create/', views.create_contract_view, name='create_contract'),
    path('publier-offre/', views.create_contract_view, name='create_contract'),
    path('postuler/<int:mission_id>/', views.apply_to_mission_view, name='apply_to_mission'),
    path('liste/', views.contract_list_view, name='contract_list'),
    path('<int:pk>/', views.mission_detail_view, name='mission_detail'),
]