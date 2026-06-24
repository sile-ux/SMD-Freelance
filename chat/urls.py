# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.latest_chat, name='latest_chat'),
    path('my-threads/', views.my_threads, name='my_threads'),
    path('thread/<int:user_id>/', views.start_thread, name='start_thread'),
    path('freelance-messages/', views.freelance_messages, name='freelance_messages'),
    path('room/<int:thread_id>/', views.chat_room, name='chat_room'),
    path('api/contact/<int:user_id>/', views.start_or_get_thread, name='api_start_thread'),
    path('api/room/<int:thread_id>/', views.thread_detail_api, name='api_thread_detail'),
    path('api/room/<int:thread_id>/send/', views.send_message_api, name='api_send_message'),
]