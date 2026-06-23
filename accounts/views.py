# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from .forms import FreelanceRegisterForm, ClientRegisterForm
from .models import User, FreelanceProfile, ClientProfile, ContactMessage, Newsletter, Wallet, Transaction
from contracts.models import Mission, Contract
from contracts.forms import QuickMissionForm


def home_view(request):
    query = request.GET.get('search', '')
    skills_query = request.GET.get('skills', '')

    freelances = FreelanceProfile.objects.filter(is_verified=True)
    if query:
        freelances = freelances.filter(Q(title__icontains=query) | Q(user__username__icontains=query))
    if skills_query:
        freelances = freelances.filter(skills__icontains=skills_query)

    missions = Mission.objects.all().order_by('-created_at')

    if request.method == 'POST':
        # ── Mission form ───────────────────────────────
        if 'action' in request.POST and request.POST['action'] == 'mission':
            form = QuickMissionForm(request.POST)
            if form.is_valid():
                if not request.user.is_authenticated:
                    request.session['pending_mission'] = form.cleaned_data
                    messages.info(request, "Mission configurée ! Créez votre compte pour la mettre en ligne.")
                    return redirect('accounts:register_client')
                else:
                    mission = form.save(commit=False)
                    mission.client = request.user
                    mission.save()
                    messages.success(request, "Votre mission a été publiée avec succès !")
                    return redirect('accounts:home')
            else:
                for field, errors in form.errors.items():
                    for err in errors:
                        messages.error(request, f"{field}: {err}")

        # ── Contact form ───────────────────────────────
        elif 'action' in request.POST and request.POST['action'] == 'contact':
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            subject = request.POST.get('subject', '').strip()
            message = request.POST.get('message', '').strip()
            if name and email and message:
                ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
                messages.success(request, "Message envoyé ! Nous vous répondrons dans les 24h.")
            else:
                messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('accounts:home')

        # ── Newsletter form ─────────────────────────────
        elif 'action' in request.POST and request.POST['action'] == 'newsletter':
            email = request.POST.get('email', '').strip()
            if email:
                Newsletter.objects.get_or_create(email=email)
                messages.success(request, "Inscription réussie à la newsletter !")
            else:
                messages.error(request, "Veuillez entrer une adresse email valide.")
            return redirect('accounts:home')

        # ── Fallback : mission form (legacy) ────────────
        else:
            form = QuickMissionForm(request.POST)
            if form.is_valid():
                if not request.user.is_authenticated:
                    request.session['pending_mission'] = form.cleaned_data
                    messages.info(request, "Mission configurée ! Créez votre compte pour la mettre en ligne.")
                    return redirect('accounts:register_client')
                else:
                    mission = form.save(commit=False)
                    mission.client = request.user
                    mission.save()
                    messages.success(request, "Votre mission a été publiée avec succès !")
                    return redirect('accounts:home')
    else:
        form = QuickMissionForm()

    return render(request, 'home.html', {
        'freelances': freelances, 'missions': missions, 'form': form, 'query': query, 'skills_query': skills_query
    })


@csrf_protect
def freelance_register_view(request):
    if request.method == 'POST':
        form = FreelanceRegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.role = User.Role.FREELANCE.value
                    user.set_password(form.cleaned_data['password'])
                    user.save()

                    FreelanceProfile.objects.create(
                        user=user,
                        title=form.cleaned_data.get('title', 'Développeur'),
                        skills=form.cleaned_data.get('skills', ''),
                        hourly_rate=form.cleaned_data.get('hourly_rate', 0.00),
                        bio=form.cleaned_data.get('bio', '')
                    )
                messages.success(request, "Compte Freelancer créé ! En attente de validation admin.")
                return redirect('accounts:login')  # AJOUTÉ : namespace 'accounts:'
            except Exception as e:
                print(f"❌ ERREUR SCRIPT FREELANCE: {e}")
                messages.error(request, "Une erreur est survenue lors de la création de votre profil.")
    else:
        form = FreelanceRegisterForm()
    return render(request, 'accounts/register_freelance.html', {'form': form})


@csrf_protect
def register_client(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')  # AJOUTÉ : namespace 'accounts:'

    if request.method == 'POST':
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.role = User.Role.CLIENT.value
                    user.set_password(form.cleaned_data['password'])
                    user.save()

                    ClientProfile.objects.create(
                        user=user,
                        compagny_name=form.cleaned_data.get('compagny_name') or form.cleaned_data.get(
                            'company_name') or '',
                        description=form.cleaned_data.get('description', '')
                    )

                    # Sauvegarde automatique de la mission anonyme stockée en session si elle existe
                    pending_mission_data = request.session.pop('pending_mission', None)
                    if pending_mission_data:
                        Mission.objects.create(
                            client=user,
                            title=pending_mission_data['title'],
                            description=pending_mission_data['description'],
                            budget=pending_mission_data['budget'],
                            skills_required=pending_mission_data['skills_required']
                        )

                login(request, user)
                messages.success(request, "Votre compte Client a été créé avec succès !")
                return redirect('accounts:dashboard')  # AJOUTÉ : namespace 'accounts:'
            except Exception as e:
                print(f"❌ ERREUR SCRIPT CLIENT : {e}")
                messages.error(request, "Une erreur est survenue lors de la création de votre profil.")
    else:
        form = ClientRegisterForm()
    return render(request, 'accounts/register_client.html', {'form': form})


@csrf_protect
def user_login(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')  # AJOUTÉ : namespace 'accounts:'
    if request.method == 'POST':
        username_input = request.POST.get('username')
        password_input = request.POST.get('password')
        user = authenticate(request, username=username_input, password=password_input)
        if user is not None:
            login(request, user)
            messages.success(request, f"Bon retour, {user.username} !")
            return redirect('accounts:dashboard')  # AJOUTÉ : namespace 'accounts:'
        else:
            messages.error(request, "Identifiants invalides.")
    return render(request, 'accounts/login.html')


def user_logout(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN.value:
        return redirect('/admin/')
    elif user.role == User.Role.FREELANCE.value:
        from contracts.models import Mission, Application
        missions = Mission.objects.filter(status='active').order_by('-created_at')
        mission_count = missions.count()
        application_count = Application.objects.filter(freelance=user).count()
        urgent_count = missions.filter(urgency='urgent').count()
        return render(request, 'accounts/dashboard_freelance.html', {
            'profile': user.freelance_profile,
            'missions': missions,
            'mission_count': mission_count,
            'application_count': application_count,
            'urgent_count': urgent_count,
        })
    elif user.role == User.Role.CLIENT.value:
        freelance_count = FreelanceProfile.objects.filter(is_verified=True).count()
        contract_count = Contract.objects.filter(client=user).count()
        recent_contracts = Contract.objects.filter(client=user).order_by('-created_at')[:5]
        freelancers = FreelanceProfile.objects.filter(is_verified=True).select_related('user').order_by('-rating')[:20]
        return render(request, 'accounts/dashboard_client.html', {
            'profile': user.client_profile,
            'freelance_count': freelance_count,
            'contract_count': contract_count,
            'recent_contracts': recent_contracts,
            'freelancers': freelancers,
        })
    return redirect('accounts:choice_register')  # AJOUTÉ : namespace 'accounts:'


@login_required
def transaction_view(request):
    user = request.user
    wallet, _ = Wallet.objects.get_or_create(user=user)
    transactions = Transaction.objects.filter(user=user)[:20]

    # Pour l'onglet Mission : contrats ouverts du client
    contracts = Contract.objects.filter(client=user, status='OPEN').order_by('-created_at') if user.role == User.Role.CLIENT.value else []
    freelancers = FreelanceProfile.objects.filter(is_verified=True).select_related('user')[:20]

    if request.method == 'POST':
        section = request.POST.get('section')

        # ── DÉPÔT ──
        if section == 'deposit':
            amount = request.POST.get('amount', '0')
            method = request.POST.get('method', 'orange')
            phone = request.POST.get('phone', '')
            try:
                amount = float(amount)
                if amount < 100:
                    messages.error(request, 'Le montant minimum est de 100 CFA.')
                    return redirect('accounts:transaction')
                fee = 0 if amount >= 50000 else (100 if amount >= 10000 else 0)
                Transaction.objects.create(
                    user=user, type='deposit', amount=amount, fee=fee,
                    method=method, status='pending', phone=phone,
                    description=f"Dépôt de {amount:,.0f} CFA via {dict(Transaction.METHOD_CHOICES).get(method, method)}"
                )
                messages.success(request, f'Demande de dépôt de {amount:,.0f} CFA enregistrée. Vous allez être redirigé vers le service de paiement.')
            except (ValueError, TypeError):
                messages.error(request, 'Montant invalide.')
            return redirect('accounts:transaction')

        # ── PAIEMENT MISSION ──
        elif section == 'mission':
            amount = request.POST.get('amount', '0')
            method = request.POST.get('method', 'orange')
            contract_id = request.POST.get('contract_id', '')
            freelance_id = request.POST.get('freelance_id', '')
            try:
                amount = float(amount)
                if amount < 100:
                    messages.error(request, 'Le montant minimum est de 100 CFA.')
                    return redirect('accounts:transaction')
                fee = round(amount * 0.05)
                total = amount + fee
                if float(wallet.balance) < total:
                    messages.error(request, f'Solde insuffisant. Vous disposez de {float(wallet.balance):,.0f} CFA.')
                    return redirect('accounts:transaction')
                contract = Contract.objects.get(id=contract_id, client=user) if contract_id else None
                freelance_user = User.objects.get(id=freelance_id) if freelance_id else None
                Transaction.objects.create(
                    user=user, type='mission_payment', amount=amount, fee=fee,
                    method=method, status='pending',
                    contract=contract, freelance=freelance_user,
                    description=f"Paiement mission '{contract.title if contract else 'N/A'}' — {amount:,.0f} CFA"
                )
                messages.success(request, f'Demande de paiement de {amount:,.0f} CFA enregistrée. En attente de confirmation.')
            except (ValueError, TypeError):
                messages.error(request, 'Montant invalide.')
            except Contract.DoesNotExist:
                messages.error(request, 'Contrat introuvable.')
            return redirect('accounts:transaction')

        # ── RETRAIT ──
        elif section == 'withdraw':
            amount = request.POST.get('amount', '0')
            method = request.POST.get('method', 'orange')
            account = request.POST.get('account', '')
            try:
                amount = float(amount)
                if amount < 100:
                    messages.error(request, 'Le montant minimum est de 100 CFA.')
                    return redirect('accounts:transaction')
                fee = round(amount * 0.015)
                total = amount + fee
                if float(wallet.balance) < total:
                    messages.error(request, f'Solde insuffisant. Vous disposez de {float(wallet.balance):,.0f} CFA.')
                    return redirect('accounts:transaction')
                if not account or len(account) < 5:
                    messages.error(request, 'Veuillez saisir un numéro de compte valide.')
                    return redirect('accounts:transaction')
                Transaction.objects.create(
                    user=user, type='withdrawal', amount=amount, fee=fee,
                    method=method, status='pending', account=account,
                    description=f"Retrait de {amount:,.0f} CFA vers {dict(Transaction.METHOD_CHOICES).get(method, method)}"
                )
                messages.success(request, f'Demande de retrait de {amount:,.0f} CFA enregistrée. Traitement sous 24-48h.')
            except (ValueError, TypeError):
                messages.error(request, 'Montant invalide.')
            return redirect('accounts:transaction')

    return render(request, 'accounts/transactions.html', {
        'wallet': wallet,
        'transactions': transactions,
        'contracts': contracts,
        'freelancers': freelancers,
    })


@login_required
def parametre_view(request):
    user = request.user
    is_client = user.role == User.Role.CLIENT.value
    profile = user.client_profile if is_client else user.freelance_profile

    if request.method == 'POST':
        section = request.POST.get('section')

        # ── Profil ──
        if section == 'profile':
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            bio = request.POST.get('bio', '').strip()
            if username:
                user.username = username
            if email:
                user.email = email
            user.save()
            profile.bio = bio
            profile.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('accounts:parametre')

        # ── Sécurité (mot de passe) ──
        elif section == 'security':
            current = request.POST.get('current_password', '')
            new_pass = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')
            if not user.check_password(current):
                messages.error(request, 'Mot de passe actuel incorrect.')
            elif len(new_pass) < 6:
                messages.error(request, 'Le nouveau mot de passe doit faire au moins 6 caractères.')
            elif new_pass != confirm:
                messages.error(request, 'Les nouveaux mots de passe ne correspondent pas.')
            else:
                user.set_password(new_pass)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Mot de passe modifié avec succès.')
            return redirect('accounts:parametre')

        # ── Notifications ──
        elif section == 'notifications':
            profile.notif_email = request.POST.get('notif_email') == 'on'
            profile.notif_push = request.POST.get('notif_push') == 'on'
            profile.notif_missions = request.POST.get('notif_missions') == 'on'
            profile.notif_messages = request.POST.get('notif_messages') == 'on'
            profile.notif_reminders = request.POST.get('notif_reminders') == 'on'
            profile.save()
            messages.success(request, 'Préférences de notifications enregistrées.')
            return redirect('accounts:parametre')

        # ── Confidentialité ──
        elif section == 'privacy':
            profile.profile_public = request.POST.get('profile_public') == 'on'
            profile.share_email = request.POST.get('share_email') == 'on'
            profile.save()
            messages.success(request, 'Paramètres de confidentialité enregistrés.')
            return redirect('accounts:parametre')

        # ── Apparence ──
        elif section == 'appearance':
            profile.theme = request.POST.get('theme', 'Clair')
            profile.language = request.POST.get('language', 'Français')
            profile.font_size = request.POST.get('font_size', 'Normale')
            profile.save()
            messages.success(request, 'Apparence mise à jour.')
            return redirect('accounts:parametre')

        # ── Préférences Missions ──
        elif section == 'preferences':
            profile.preferred_categories = request.POST.get('preferred_categories', 'Toutes')
            profile.min_budget = request.POST.get('min_budget', 'Aucun')
            profile.auto_alerts = request.POST.get('auto_alerts') == 'on'
            profile.save()
            messages.success(request, 'Préférences missions enregistrées.')
            return redirect('accounts:parametre')

        # ── Support ──
        elif section == 'support':
            subject = request.POST.get('subject', '').strip()
            message_text = request.POST.get('message', '').strip()
            if subject and message_text:
                ContactMessage.objects.create(
                    name=user.username,
                    email=user.email,
                    subject=subject,
                    message=message_text,
                )
                messages.success(request, 'Message envoyé au support. Nous vous répondrons sous 24h.')
            else:
                messages.error(request, 'Veuillez remplir tous les champs.')
            return redirect('accounts:parametre')

    return render(request, 'accounts/parametre.html', {'profile': profile, 'is_client': is_client})


def choice_register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')  # AJOUTÉ : namespace 'accounts:'
    return render(request, 'accounts/choice_register.html')