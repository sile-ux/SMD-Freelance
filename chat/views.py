# chat/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from types import SimpleNamespace
from .models import Thread, Message

User = get_user_model()


@login_required
def latest_chat(request):
    """Redirige vers la dernière discussion active de l'utilisateur"""
    if request.user.role == User.Role.FREELANCE.value:
        thread = request.user.freelance_threads.order_by('-created_at').first()
    else:
        thread = request.user.client_threads.order_by('-created_at').first()

    if thread:
        return redirect('chat:chat_room', thread_id=thread.id)
    return redirect('chat:my_threads')


@login_required
def my_threads(request):
    """Affiche la liste des discussions de l'utilisateur connecté"""
    return redirect('chat:freelance_messages')


@login_required
def start_or_get_thread(request, user_id): # 🔄 Changé freelance_id -> user_id
    """API : Initialise ou récupère un salon de discussion avec un freelance"""
    freelance = get_object_or_404(User, id=user_id)

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
def start_thread(request, user_id): # 🔄 Changé freelance_id -> user_id pour correspondre à l'URL
    """
    Crée ou récupère une discussion entre le client connecté et un freelance.
    """
    # 1. On récupère le profil du freelance ciblé via l'ID reçu dans l'URL (ex: 15)
    freelance_user = get_object_or_404(User, id=user_id)

    # Sécurité : On empêche un utilisateur de s'auto-contacter
    if request.user == freelance_user:
        return redirect('accounts:dashboard')

    # 2. On passe l'instance de l'utilisateur trouvée (freelance_user)
    thread, created = Thread.objects.get_or_create(
        client=request.user,
        freelance=freelance_user
    )

    # 3. On redirige vers la chat room dédiée
    return redirect('chat:chat_room', thread_id=thread.id)


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


@login_required
def freelance_messages(request):
    threads = get_user_threads(request.user)

    if threads:
        first_thread = threads[0]['thread']
        chat_messages = first_thread.messages.all().order_by('created_at')
        other_user = first_thread.freelance if request.user == first_thread.client else first_thread.client
        context = {
            'thread': first_thread,
            'chat_messages': chat_messages,
            'other_user': other_user,
            'threads': threads,
        }
    else:
        context = {
            'thread': SimpleNamespace(id=0),
            'chat_messages': [],
            'other_user': None,
            'threads': [],
        }

    return render(request, 'chat/chat_room-FREE.html', context)


def get_user_threads(user):
    """Retourne tous les threads de l'utilisateur avec métadonnées"""
    if user.role == User.Role.FREELANCE.value:
        threads_qs = user.freelance_threads.all()
    else:
        threads_qs = user.client_threads.all()

    threads = []
    for t in threads_qs:
        last_msg = t.messages.order_by('-created_at').first()
        unread = t.messages.filter(is_read=False).exclude(sender=user).count()
        other_user = t.freelance if user == t.client else t.client
        threads.append({
            'thread': t,
            'last_message': last_msg,
            'unread_count': unread,
            'other_user': other_user,
        })
    return threads


@login_required
def chat_room(request, thread_id):
    """Affiche une salle de discussion spécifique et ses messages."""
    thread = get_object_or_404(Thread, id=thread_id)

    if request.user != thread.client and request.user != thread.freelance:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Message.objects.create(thread=thread, sender=request.user, text=text)
        return redirect('chat:chat_room', thread_id=thread.id)

    chat_messages = thread.messages.all().order_by('created_at')
    other_user = thread.freelance if request.user == thread.client else thread.client
    threads = get_user_threads(request.user)

    context = {
        'thread': thread,
        'chat_messages': chat_messages,
        'other_user': other_user,
        'threads': threads,
    }
    return render(request, 'chat/chat_room-FREE.html', context)