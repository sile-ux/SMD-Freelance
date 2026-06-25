import json
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404

from .models import Mission, Application, Contract
from .forms import QuickMissionForm
from .templatetags.contracts_extras import to_fcfa
User = get_user_model()


def contract_list_view(request):
    missions = Mission.objects.filter(status='open').order_by('-created_at')
    contracts = Contract.objects.all().order_by('-created_at')

    missions_data = []
    for m in missions:
        missions_data.append({
            'id': m.id,
            'title': m.title,
            'description': m.description,
            'client': m.client.username if m.client else 'Anonyme',
            'budget': float(m.budget),
            'status': m.status,
            'category': m.category,
            'skills': m.tag_list,
            'urgency': m.urgency,
            'date': m.created_at.strftime('%Y-%m-%d') if m.created_at else '',
            'location': m.location,
            'duration': m.duration,
            'payment_type': m.payment_type,
            'currency': m.currency,
            'budget_fcfa': to_fcfa(m.budget, m.currency),
            'extra_info': m.extra_info or '',
        })

    return render(request, 'contracts/contract_list.html', {
        'missions_json': missions_data,
        'missions': missions,
        'contracts': contracts,
    })


def freelance_list_api(request):
    freelances = User.objects.filter(role='FREELANCE').values('id', 'username', 'email')
    return JsonResponse({
        "status": "success",
        "freelances": list(freelances)
    })


def mission_list_api(request):
    missions = Mission.objects.all().order_by('-created_at').values(
        'id', 'title', 'description', 'budget', 'skills_required'
    )
    return JsonResponse({
        "status": "success",
        "total_missions": missions.count(),
        "missions": list(missions)
    })


def tarifs_api(request):
    grille_tarifs = {
        "Développeur Junior": "15,000 - 30,000 CFA/jour",
        "Développeur Mid-level": "40,000 - 75,000 CFA/jour",
        "Expert / Senior": "150,000+ CFA/jour",
        "DevOps / Cloud": "100,000+ CFA/jour"
    }
    return JsonResponse({
        "status": "success",
        "devise": "CFA",
        "grille": grille_tarifs
    })


@login_required
def create_contract_view(request):
    if hasattr(request.user, 'role') and request.user.role != 'CLIENT':
        messages.error(request, "Seuls les profils Clients peuvent publier des offres.")
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = QuickMissionForm(request.POST)
        if form.is_valid():
            mission = form.save(commit=False)
            mission.client = request.user
            mission.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Mission publiée avec succès !'})
            messages.success(request, "Mission publiée avec succès !")
            return redirect('contracts:contract_list')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Erreur de validation',
                'errors': form.errors,
            }, status=400)
    else:
        form = QuickMissionForm()

    return render(request, 'contracts/create-contract.html', {'form': form})


def mission_detail_view(request, pk):
    mission = get_object_or_404(Mission, pk=pk)

    user = request.user
    unread_count = 0
    if user.is_authenticated:
        from chat.models import Thread, Message
        if user.role == User.Role.FREELANCE.value:
            user_threads = user.freelance_threads.all()
        else:
            user_threads = user.client_threads.all()
        unread_count = sum(
            t.messages.filter(is_read=False).exclude(sender=user).count()
            for t in user_threads
        )

    return render(request, 'contracts/mission_detail.html', {
        'mission': mission,
        'unread_count': unread_count,
    })


@login_required
def apply_to_mission_view(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)

    if hasattr(request.user, 'role') and request.user.role != 'FREELANCE':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Seuls les freelances peuvent postuler.'})
        messages.error(request, "Seuls les profils Freelances peuvent postuler aux offres.")
        return redirect('accounts:home')

    if mission.client == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Vous ne pouvez pas postuler à votre propre mission.'})
        messages.error(request, "Vous ne pouvez pas postuler à votre propre mission.")
        return redirect('accounts:home')

    # Vérification que le freelance est approuvé par l'admin
    if not (hasattr(request.user, 'freelance_profile') and request.user.freelance_profile.is_verified):
        try:
            from chat.models import Thread, Message
            admin = User.objects.filter(is_superuser=True, is_staff=True).first()
            if admin:
                if admin.role == User.Role.FREELANCE.value:
                    thread, _ = Thread.objects.get_or_create(client=request.user, freelance=admin)
                else:
                    thread, _ = Thread.objects.get_or_create(client=admin, freelance=request.user)
                Message.objects.create(
                    thread=thread,
                    sender=admin,
                    text=f"Bonjour {request.user.username}, votre compte freelance est en cours de validation "
                         f"par l'administration. Veuillez attendre d'être vérifié avant de postuler aux missions."
                )
        except Exception:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Votre compte doit être vérifié par l\'administration avant de pouvoir postuler.'})
        messages.error(request, "Votre compte doit être vérifié par l'administration avant de pouvoir postuler.")
        return redirect('accounts:home')

    already_applied = Application.objects.filter(mission=mission, freelance=request.user).exists()
    if already_applied:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'warning', 'message': 'Vous avez déjà postulé.'})
        messages.warning(request, "Vous avez déjà candidaté à cette offre.")
    else:
        Application.objects.create(mission=mission, freelance=request.user)

        # Messages automatiques si le freelance est vérifié
        try:
            if (hasattr(request.user, 'freelance_profile') and
                request.user.freelance_profile.is_verified):

                from chat.models import Thread, Message

                thread, _ = Thread.objects.get_or_create(
                    client=mission.client,
                    freelance=request.user
                )

                profile = request.user.freelance_profile
                skills = ', '.join(profile.skill_list[:5]) if profile.skill_list else 'Non renseignées'

                # Message du freelance au client
                Message.objects.create(
                    thread=thread,
                    sender=request.user,
                    text=f"Bonjour, je viens de postuler à votre mission « {mission.title} ». "
                         f"Voici mon profil : {request.user.username} | {profile.title or 'Freelance'} "
                         f"({to_fcfa(profile.hourly_rate, 'EUR'):,.0f} FCFA/h) — Compétences : {skills}. "
                         f"N'hésitez pas à me contacter pour plus d'informations."
                )

                # Message de confirmation au freelance
                Message.objects.create(
                    thread=thread,
                    sender=mission.client,
                    text=f"Bonjour {request.user.username}, votre candidature pour la mission "
                         f"« {mission.title} » a bien été reçue. Le client vous recontactera "
                         f"si votre profil est retenu."
                )
        except Exception:
            pass  # Ne pas bloquer la candidature si l'envoi automatique échoue

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Candidature envoyée !'})
        messages.success(request, f"Candidature envoyée pour '{mission.title}' !")

    return redirect('contracts:contract_list')

