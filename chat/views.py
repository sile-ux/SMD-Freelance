# chat/views.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from .models import Thread, Message

User = get_user_model()


@login_required
def start_or_get_thread(request, freelance_id):
    """API : Initialise ou récupère un salon de discussion avec un freelance"""
    freelance = get_object_or_404(User, id=freelance_id)

    if request.user == freelance:
        return JsonResponse({"error": "Vous ne pouvez pas discuter avec vous-même."}, status=400)

    # Récupère ou crée le salon entre le client (request.user) et le freelance
    thread, created = Thread.objects.get_or_create(
        client=request.user,
        freelance=freelance
    )

    return JsonResponse({
        "status": "success",
        "thread_id": thread.id,
        "created_now": created,
        "client": thread.client.username,
        "freelance": thread.freelance.username
    })


@login_required
def thread_detail_api(request, thread_id):
    """API : Récupère l'historique des messages d'un salon spécifique"""
    thread = get_object_or_404(Thread, id=thread_id)

    # SÉCURITÉ BACKEND : L'utilisateur fait-il partie de ce chat ?
    if request.user != thread.client and request.user != thread.freelance:
        return JsonResponse({"error": "Accès interdit à ce salon de discussion."}, status=403)

    # Récupérer tous les messages du salon
    messages = thread.messages.all()
    messages_data = [
        {
            "id": msg.id,
            "sender": msg.sender.username,
            "text": msg.text,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_read": msg.is_read
        }
        for msg in messages
    ]

    return JsonResponse({
        "thread_id": thread.id,
        "client": thread.client.username,
        "freelance": thread.freelance.username,
        "messages": messages_data
    })


@login_required
def send_message_api(request, thread_id):
    """API : Envoie un message dans un salon via une requête POST"""
    if request.method == 'POST':
        thread = get_object_or_404(Thread, id=thread_id)

        # SÉCURITÉ BACKEND : L'expéditeur fait-il partie du chat ?
        if request.user != thread.client and request.user != thread.freelance:
            return JsonResponse({"error": "Action interdite."}, status=403)

        # On accepte du texte classique ou du JSON en entrée
        import json
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
        except json.JSONDecodeError:
            text = request.POST.get('text', '').strip()

        if not text:
            return JsonResponse({"error": "Le message ne peut pas être vide."}, status=400)

        # Création du message en base
        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            text=text
        )

        return JsonResponse({
            "status": "Message envoyé",
            "message_id": message.id,
            "sender": message.sender.username,
            "text": message.text
        }, status=201)

    return JsonResponse({"error": "Méthode non autorisée. Utilisez POST."}, status=405)