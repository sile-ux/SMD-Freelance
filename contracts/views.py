# À rajouter à la fin de contracts/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404

from .models import Mission, Application  # Ou Contract selon ton choix de modèle principal
from .forms import QuickMissionForm
User = get_user_model()


def freelance_list_api(request):
    """Backend : Récupère la liste des profils Freelance uniquement"""
    # On filtre les utilisateurs. (Adapte 'is_freelance' selon le nom de ton champ dans ton CustomUser)
    # Si tu as un champ user_type, ce serait : filter(user_type='FREELANCE')
    freelances = User.objects.filter(role='FREELANCE').values('id', 'username', 'email')

    return JsonResponse({
        "status": "success",
        "freelances": list(freelances)
    })


def mission_list_api(request):
    """Backend : Récupère toutes les missions disponibles en base de données"""
    # On récupère les missions de la plus récente à la plus ancienne
    missions = Mission.objects.all().order_by('-created_at').values('id', 'title', 'description', 'budget',
                                                                    'skills_required')

    return JsonResponse({
        "status": "success",
        "total_missions": missions.count(),
        "missions": list(missions)
    })


def tarifs_api(request):
    """Backend : Renvoie la grille tarifaire de référence en CFA"""
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
    """
    Vue permettant à un client connecté de publier une nouvelle offre/mission
    depuis son tableau de bord.
    """
    # Optionnel : Sécurité pour s'assurer que seul un client peut publier
    if hasattr(request.user, 'role') and request.user.role != 'CLIENT':
        messages.error(request, "Seuls les profils Clients peuvent publier des offres.")
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = QuickMissionForm(request.POST)
        if form.is_valid():
            mission = form.save(commit=False)
            mission.client = request.user  # Associe l'offre au client connecté
            mission.save()
            messages.success(request, "🚀 Votre nouvelle offre a été publiée avec succès !")
            return redirect('accounts:dashboard')
    else:
        form = QuickMissionForm()

    return render(request, 'contracts/create_contract.html', {'form': form})

@login_required
def apply_to_mission_view(request, mission_id):
    """
    Permet à un freelance de postuler instantanément à une offre.
    """
    mission = get_object_or_404(Mission, id=mission_id)

    # Sécurité : Vérifier si l'utilisateur est bien un freelance
    if hasattr(request.user, 'role') and request.user.role != 'FREELANCE':
        messages.error(request, "Seuls les profils Freelances peuvent postuler aux offres.")
        return redirect('accounts:home')

    # Sécurité : Empêcher le client de postuler sa propre offre
    if mission.client == request.user:
        messages.error(request, "Vous ne pouvez pas postuler à votre propre mission.")
        return redirect('accounts:home')

    # Vérifier si le freelance a déjà postulé
    already_applied = Application.objects.filter(mission=mission, freelancer=request.user).exists()
    if already_applied:
        messages.warning(request, "Vous avez déjà candidaté à cette offre de mission.")
    else:
        # Création de la candidature
        Application.objects.create(mission=mission, freelancer=request.user)
        messages.success(request, f"🚀 Votre candidature pour '{mission.title}' a été envoyée avec succès !")

    return redirect('accounts:home')