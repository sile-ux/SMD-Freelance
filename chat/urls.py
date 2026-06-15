# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Route pour initier le contact avec un freelance : /chat/contact/<id_freelance>/
    path('contact/<int:freelance_id>/', views.start_or_get_thread, name='start_thread'),

    # Route pour charger l'historique d'un chat : /chat/room/<id_salon>/
    path('room/<int:thread_id>/', views.thread_detail_api, name='thread_detail'),

    # Route pour envoyer un message : /chat/room/<id_salon>/send/
    path('room/<int:thread_id>/send/', views.send_message_api, name='send_message'),
]