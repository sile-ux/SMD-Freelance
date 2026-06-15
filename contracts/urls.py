
from django.urls import path
from . import views

urlpatterns = [
    path('', views.contract_list, name='contract_list'),
    path('nouveau/', views.create_contract, name='create_contract'),
    path('<int:contract_id>/postuler/', views.apply_to_contract, name='apply_contract'),
]