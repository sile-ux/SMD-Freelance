# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
import json
from .forms import FreelanceRegisterForm, ClientRegisterForm
from .models import User, FreelanceProfile, ClientProfile, ContactMessage, Newsletter, Wallet, Transaction, Dispute, Document
from contracts.models import Mission, Contract, Application
from contracts.forms import QuickMissionForm
from contracts.templatetags.contracts_extras import to_fcfa


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

    # Compteur de messages non lus
    from chat.models import Thread, Message
    if user.role == User.Role.FREELANCE.value:
        user_threads = user.freelance_threads.all()
    else:
        user_threads = user.client_threads.all()
    unread_count = sum(
        t.messages.filter(is_read=False).exclude(sender=user).count()
        for t in user_threads
    )

    if user.is_superuser or user.role == User.Role.ADMIN.value:
        return redirect('accounts:admin_dashboard')
    elif user.role == User.Role.FREELANCE.value:
        from contracts.models import Mission, Application
        from django.db.models import Count
        missions = Mission.objects.filter(status='open').select_related('client').order_by('-created_at')
        mission_count = missions.count()
        applications = Application.objects.filter(freelance=user).select_related('mission').order_by('-created_at')
        application_count = applications.count()
        urgent_count = missions.filter(urgency='high').count()
        return render(request, 'accounts/dashboard_freelance.html', {
            'profile': user.freelance_profile,
            'missions': missions,
            'applications': applications,
            'mission_count': mission_count,
            'application_count': application_count,
            'urgent_count': urgent_count,
            'unread_count': unread_count,
        })
    elif user.role == User.Role.CLIENT.value:
        from contracts.models import Mission as ClientMission, Application
        from django.db.models import Prefetch
        freelance_count = FreelanceProfile.objects.filter(is_verified=True).count()
        contract_count = Contract.objects.filter(client=user).count()
        recent_contracts = Contract.objects.filter(client=user).order_by('-created_at')[:5]
        freelancers = FreelanceProfile.objects.filter(is_verified=True).select_related('user').order_by('-rating')[:20]
        client_missions = ClientMission.objects.filter(client=user).prefetch_related(
            Prefetch('applications',
                queryset=Application.objects.select_related(
                    'freelance', 'freelance__freelance_profile'
                ).order_by('-created_at'))
        ).order_by('-created_at')
        return render(request, 'accounts/dashboard_client.html', {
            'profile': user.client_profile,
            'freelance_count': freelance_count,
            'contract_count': contract_count,
            'recent_contracts': recent_contracts,
            'freelancers': freelancers,
            'client_missions': client_missions,
            'unread_count': unread_count,
        })
    return redirect('accounts:choice_register')


@login_required
def admin_dashboard(request):
    user = request.user
    if not (user.is_superuser or user.role == User.Role.ADMIN.value):
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('accounts:dashboard')

    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Stats
    total_users = User.objects.count()
    active_freelances = FreelanceProfile.objects.filter(is_verified=True).count()
    total_freelances = FreelanceProfile.objects.count()
    pending_freelances = FreelanceProfile.objects.filter(is_verified=False).count()
    total_clients = ClientProfile.objects.count()
    active_missions = Mission.objects.filter(status='open').count()
    pending_missions = Mission.objects.filter(status='pending').count()
    completed_missions = Mission.objects.filter(status='completed').count()
    total_missions = Mission.objects.count()

    # Revenus
    monthly_revenue = Transaction.objects.filter(
        created_at__gte=month_start, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Transaction.objects.filter(status='completed').aggregate(
        total=Sum('amount'))['total'] or 0
    pending_payments = Transaction.objects.filter(status='pending').aggregate(
        total=Sum('amount'))['total'] or 0

    # Paiements du mois (pour la section paiements)
    monthly_payments = monthly_revenue
    pending_payments_amount = pending_payments
    processing_payments = Transaction.objects.filter(status='pending').count()

    # Utilisateurs récents
    recent_users = User.objects.order_by('-last_login')[:8]

    # Freelances en attente
    pending_freelance_list = FreelanceProfile.objects.filter(is_verified=False).select_related('user')[:20]

    # Litiges
    disputes = Dispute.objects.all().order_by('-created_at')[:10]
    open_disputes = Dispute.objects.filter(status='open').count()
    in_progress_disputes = Dispute.objects.filter(status='in_progress').count()

    # Missions count
    mission_counts = {
        'total': total_missions,
        'active': active_missions,
        'pending': pending_missions,
        'completed': completed_missions,
    }

    # Calcul des tendances (pour les badges up/down)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_users = User.objects.filter(date_joined__lt=month_start, date_joined__gte=last_month_start).count()
    if prev_users > 0:
        user_change = int((total_users - prev_users) / prev_users * 100)
    else:
        user_change = 0
    user_trend = 'up' if user_change >= 0 else 'down'

    prev_freelances = FreelanceProfile.objects.filter(create_at__lt=month_start, create_at__gte=last_month_start).count()
    if prev_freelances > 0:
        freelance_change = int((total_freelances - prev_freelances) / prev_freelances * 100)
    else:
        freelance_change = 0
    freelance_trend = 'up' if freelance_change >= 0 else 'down'

    prev_revenue = Transaction.objects.filter(
        created_at__lt=month_start, created_at__gte=last_month_start, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    if prev_revenue > 0:
        revenue_change = int((monthly_revenue - prev_revenue) / prev_revenue * 100)
    else:
        revenue_change = 0
    revenue_trend = 'up' if revenue_change >= 0 else 'down'

    prev_missions = Mission.objects.filter(created_at__lt=month_start, created_at__gte=last_month_start).count()
    if prev_missions > 0:
        mission_change = int((total_missions - prev_missions) / prev_missions * 100)
    else:
        mission_change = 0
    mission_trend = 'up' if mission_change >= 0 else 'down'

    # Messages non lus pour l'admin
    from chat.models import Thread, Message
    admin_threads = user.client_threads.all()
    unread_count = sum(
        t.messages.filter(is_read=False).exclude(sender=user).count()
        for t in admin_threads
    )

    # Badges pour la sidebar
    sidebar_badges = {
        'users': total_users,
        'pending_freelances': pending_freelances,
        'pending_payments': Transaction.objects.filter(status='pending').count(),
        'open_disputes': open_disputes + in_progress_disputes,
        'missions': active_missions,
        'notifications': unread_count + pending_freelances + pending_payments,
    }

    context = {
        'admin_user': user,
        'total_users': total_users,
        'active_freelances': active_freelances,
        'monthly_revenue': monthly_revenue,
        'active_missions': active_missions,
        'recent_users': recent_users,
        'pending_freelance_list': pending_freelance_list,
        'disputes': disputes,
        'total_revenue': total_revenue,
        'monthly_payments': monthly_payments,
        'pending_payments_amount': pending_payments_amount,
        'processing_payments': processing_payments,
        'mission_counts': mission_counts,
        'sidebar_badges': sidebar_badges,
        'user_change': abs(user_change),
        'user_trend': user_trend,
        'freelance_change': abs(freelance_change),
        'freelance_trend': freelance_trend,
        'revenue_change': abs(revenue_change),
        'revenue_trend': revenue_trend,
        'mission_change': abs(mission_change),
        'mission_trend': mission_trend,
        'freelance_count': total_freelances,
        'client_count': total_clients,
        'unread_count': unread_count,
    }
    return render(request, 'accounts/dashbord_admin.html', context)


@login_required
def transaction_view(request):
    user = request.user
    wallet, _ = Wallet.objects.get_or_create(user=user)
    transactions = Transaction.objects.filter(user=user)[:20]

    # Pour l'onglet Mission : contrats ouverts du client
    contracts = Contract.objects.filter(client=user, status='OPEN').order_by('-created_at') if user.role == User.Role.CLIENT.value else []
    freelancers = FreelanceProfile.objects.filter(is_verified=True).select_related('user')[:20]

    # Candidature à accepter (depuis le bouton "Accepter" du dashboard)
    pending_application = None
    app_id = request.GET.get('accept_application') or request.POST.get('application_id')
    if app_id:
        try:
            from contracts.models import Application
            pending_application = Application.objects.select_related(
                'mission', 'freelance', 'freelance__freelance_profile'
            ).get(id=app_id, mission__client=user, status='pending')
        except Application.DoesNotExist:
            pass

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

        # ── ACCEPTATION CANDIDATURE AVEC PAIEMENT ──
        elif section == 'accept_application' and pending_application:
            try:
                amount = float(pending_application.mission.budget)
                if float(wallet.balance) < amount:
                    messages.error(
                        request,
                        f'Solde insuffisant. Vous disposez de {float(wallet.balance):,.0f} CFA, '
                        f'le montant de la mission est de {amount:,.0f} CFA.'
                    )
                    return redirect(f'{request.path}?accept_application={pending_application.id}')

                # Débiter le client
                wallet.balance -= amount
                wallet.save()

                # Créditer l'admin (premier superuser)
                admin_user = User.objects.filter(is_superuser=True).first()
                if admin_user:
                    admin_wallet, _ = Wallet.objects.get_or_create(user=admin_user)
                    admin_wallet.balance += amount
                    admin_wallet.save()

                # Enregistrer la transaction côté client
                Transaction.objects.create(
                    user=user, type='mission_payment', amount=amount, fee=0,
                    method='wallet', status='completed',
                    freelance=pending_application.freelance,
                    description=f"Paiement mission « {pending_application.mission.title} » — {amount:,.0f} CFA"
                )
                # Enregistrer la transaction côté admin
                Transaction.objects.create(
                    user=admin_user or user, type='transfer', amount=amount, fee=0,
                    method='wallet', status='completed',
                    freelance=pending_application.freelance,
                    description=f"Réception paiement mission « {pending_application.mission.title} » — {amount:,.0f} CFA"
                )

                # Accepter la candidature
                pending_application.status = 'accepted'
                pending_application.save()

                # Passer la mission en cours
                mission = pending_application.mission
                mission.status = 'in-progress'
                mission.save()

                # Refuser les autres candidatures
                from contracts.models import Application
                Application.objects.filter(mission=mission, status='pending').exclude(id=pending_application.id).update(status='rejected')

                # Notifier le freelance
                try:
                    from chat.models import Thread, Message
                    thread, _ = Thread.objects.get_or_create(
                        client=mission.client,
                        freelance=pending_application.freelance
                    )
                    Message.objects.create(
                        thread=thread,
                        sender=user,
                        text=f"Félicitations ! Votre candidature pour la mission « {mission.title} » a été acceptée "
                             f"et le paiement de {amount:,.0f} CFA a été transféré à l'administration. "
                             f"La mission peut maintenant commencer."
                    )
                except Exception:
                    pass

                messages.success(request, f'Candidature acceptée et paiement de {amount:,.0f} CFA effectué. La mission est en cours.')
                return redirect('accounts:transaction')

            except (ValueError, TypeError):
                messages.error(request, 'Erreur lors du traitement du paiement.')
            return redirect(f'{request.path}?accept_application={pending_application.id}' if pending_application else 'accounts:transaction')

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
        'pending_application': pending_application,
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
        return redirect('accounts:dashboard')
    return render(request, 'accounts/choice_register.html')


import json

def freelance_list_view(request):
    freelances = FreelanceProfile.objects.filter(is_verified=True).select_related('user').order_by('-rating')

    # Messages non lus
    user = request.user
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
    else:
        unread_count = 0

    freelances_data = []
    for f in freelances:
        avatar_name = f.user.username[:2].upper() if len(f.user.username) >= 2 else (f.user.username[0].upper() if f.user.username else '?')
        category_map = {
            'web': 'Developpement Web', 'design': 'Design', 'marketing': 'Marketing Digital',
            'writing': 'Redaction', 'video': 'Video', 'translation': 'Traduction',
        }
        specialty = (f.specialty or f.skill_list[0] if f.skill_list else 'general').lower()
        category = 'Developpement Web'
        for key, val in category_map.items():
            if key in specialty:
                category = val
                break

        avatar_class_map = {
            'Developpement Web': 'dev', 'Design': 'designer',
            'Marketing Digital': 'marketing', 'Redaction': 'writer',
            'Video': 'designer', 'Traduction': 'writer',
        }
        avatar_class = avatar_class_map.get(category, 'freelance')

        status = 'available' if f.is_verified else 'unavailable'

        freelances_data.append({
            'id': f.id,
            'name': f.user.username,
            'title': f.title,
            'category': category,
            'languages': ['Français', 'Anglais'],
            'domain': 'Tech',
            'rating': float(f.rating),
            'reviews': 0,
            'rate': float(f.hourly_rate),
            'rate_fcfa': to_fcfa(f.hourly_rate, 'EUR'),
            'status': status,
            'skills': f.skill_list,
            'avatar': avatar_name,
            'avatarClass': avatar_class,
            'description': f.bio or f"Freelance {f.title} disponible sur FreelanceHub",
        })

    return render(request, 'accounts/liste_freelanceur.html', {
        'freelances_json': freelances_data,
        'unread_count': unread_count,
    })


@login_required
def stat_freelancer_view(request):
    user = request.user
    profile = getattr(user, 'freelance_profile', None)
    wallet = getattr(user, 'wallet', None)

    # Wallet
    balance = float(wallet.balance) if wallet else 0

    # Applications
    applications = Application.objects.filter(freelance=user)
    total_apps = applications.count()
    missions_completed = applications.filter(mission__status='closed').count()
    missions_in_progress = applications.filter(mission__status='in-progress').count()

    # Rating
    rating = float(profile.rating) if profile else 4.5

    # Revenue
    txns = Transaction.objects.filter(freelance=user)
    total_revenue = txns.filter(type='mission_payment', status='completed').aggregate(s=Sum('amount'))['s'] or 0
    total_revenue = float(total_revenue)

    # Distinct clients from completed missions
    completed_mission_ids = applications.filter(mission__status='closed').values_list('mission_id', flat=True)
    total_clients = Mission.objects.filter(id__in=completed_mission_ids).values('client').distinct().count()

    # Transaction history
    transaction_history = txns.order_by('-created_at')[:20]

    # Monthly revenue (last 12 months)
    now = timezone.now()
    monthly_labels = []
    monthly_values = []
    for i in range(11, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            month_end = now
        else:
            next_month = (month_start + timedelta(days=32)).replace(day=1)
            month_end = next_month - timedelta(seconds=1)
        month_rev = txns.filter(
            type='mission_payment', status='completed',
            created_at__gte=month_start, created_at__lte=month_end
        ).aggregate(s=Sum('amount'))['s'] or 0
        monthly_labels.append(month_start.strftime('%b'))
        monthly_values.append(float(month_rev))

    # Mission status distribution
    status_counts = {
        'completed': missions_completed,
        'in_progress': missions_in_progress,
        'pending': applications.filter(mission__status='open').count(),
    }
    success_rate = round((missions_completed / total_apps * 100) if total_apps > 0 else 0)

    # Period data for JS switching
    period_data = {}
    for period_name, days in [('week', 7), ('month', 30), ('quarter', 90), ('year', 365)]:
        start = now - timedelta(days=days)
        period_txns = txns.filter(created_at__gte=start)
        period_rev = period_txns.filter(type='mission_payment', status='completed').aggregate(s=Sum('amount'))['s'] or 0
        period_missions = applications.filter(created_at__gte=start, mission__status='closed').count()
        period_clients = Mission.objects.filter(
            id__in=applications.filter(created_at__gte=start, mission__status='closed').values_list('mission_id', flat=True)
        ).values('client').distinct().count()
        period_data[period_name] = {
            'revenue': float(period_rev),
            'missions': period_missions,
            'clients': period_clients,
            'rating': rating,
        }

    context = {
        'balance': balance,
        'total_revenue': total_revenue,
        'missions_completed': missions_completed,
        'missions_in_progress': missions_in_progress,
        'average_rating': rating,
        'total_clients': total_clients,
        'total_applications': total_apps,
        'success_rate': success_rate,
        'status_counts_json': json.dumps(status_counts),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_values_json': json.dumps(monthly_values),
        'period_data_json': json.dumps(period_data),
        'transactions': transaction_history,
    }
    return render(request, 'accounts/stat_freelancer.html', context)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@login_required
def admin_api_data(request):
    """Endpoint JSON pour les données dynamiques du dashboard admin"""
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN.value):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    from django.db.models import Sum, Count
    from django.utils import timezone
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    data_type = request.GET.get('type', '')

    if data_type == 'users':
        users = User.objects.all().order_by('-date_joined')
        users_data = []
        for u in users:
            profile = getattr(u, 'freelance_profile', None) or getattr(u, 'client_profile', None)
            role_map = {'ADMIN': 'Admin', 'FREELANCE': 'Freelance', 'CLIENT': 'Client'}
            initials = (u.first_name or u.username)[:2].upper()
            av_class = 'admin' if u.role == 'ADMIN' else 'freelance' if u.role == 'FREELANCE' else 'client'
            online = 'online' if (u.last_login and (now - u.last_login).seconds < 300) else 'offline'
            users_data.append({
                'id': u.id,
                'name': u.get_full_name() or u.username,
                'username': u.username,
                'email': u.email,
                'role': role_map.get(u.role, 'Client'),
                'role_raw': u.role,
                'status': 'active' if u.is_active else 'suspended',
                'online': online,
                'date': u.date_joined.strftime('%d/%m/%Y'),
                'initials': initials,
                'avClass': av_class,
                'is_verified': profile.is_verified if hasattr(profile, 'is_verified') else True,
            })
        return JsonResponse({'users': users_data})

    if data_type == 'freelances_pending':
        freelances = FreelanceProfile.objects.filter(is_verified=False).select_related('user')
        data = []
        for f in freelances:
            initials = (f.user.first_name or f.user.username)[:2].upper()
            data.append({
                'id': f.id,
                'user_id': f.user.id,
                'name': f.user.get_full_name() or f.user.username,
                'email': f.user.email,
                'skills': f.skills,
                'initials': initials,
                'doc_count': 3,
            })
        return JsonResponse({'freelances': data})

    if data_type == 'disputes':
        disputes_list = Dispute.objects.select_related('freelance', 'client').all()
        data = []
        for d in disputes_list:
            status_map = {'open': '🟠 Ouvert', 'in_progress': '🟡 En cours', 'resolved': '✅ Résolu'}
            data.append({
                'id': d.id,
                'ref': f"LIT-{d.created_at.year}-{str(d.id).zfill(3)}",
                'status': d.status,
                'status_label': status_map.get(d.status, d.status),
                'freelance': d.freelance.username,
                'client': d.client.username,
                'reason': d.reason[:80],
                'amount': float(d.amount),
                'created_at': d.created_at.strftime('%d/%m/%Y'),
            })
        return JsonResponse({'disputes': data})

    if data_type == 'stats':
        total_users = User.objects.count()
        active_freelances = FreelanceProfile.objects.filter(is_verified=True).count()
        monthly_revenue = Transaction.objects.filter(
            created_at__gte=month_start, status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        active_missions = Mission.objects.filter(status='open').count()
        return JsonResponse({
            'total_users': total_users,
            'active_freelances': active_freelances,
            'monthly_revenue': float(monthly_revenue),
            'active_missions': active_missions,
        })

    if data_type == 'settings':
        from .models import PlatformSettings
        s = PlatformSettings.get_instance()
        return JsonResponse({
            'site_name': s.site_name,
            'site_description': s.site_description,
            'support_email': s.support_email,
            'default_currency': s.default_currency,
            'commission_rate': float(s.commission_rate),
            'min_payout': float(s.min_payout),
            'max_payout': float(s.max_payout),
            'enable_registrations': s.enable_registrations,
            'auto_validate_freelances': s.auto_validate_freelances,
            'maintenance_mode': s.maintenance_mode,
            'notif_new_user': s.notif_new_user,
            'notif_new_mission': s.notif_new_mission,
            'notif_payment': s.notif_payment,
            'notif_dispute': s.notif_dispute,
            'facebook_url': s.facebook_url,
            'twitter_url': s.twitter_url,
            'linkedin_url': s.linkedin_url,
            'meta_keywords': s.meta_keywords,
            'meta_description': s.meta_description,
        })

    return JsonResponse({'error': 'Invalid type'}, status=400)


@login_required
@csrf_exempt
def admin_api_action(request):
    """Endpoint pour les actions admin (validate, suspend, resolve, etc.)"""
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN.value):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    action = data.get('action', '')

    if action == 'validate_freelance':
        user_id = data.get('user_id')
        try:
            profile = FreelanceProfile.objects.get(user_id=user_id)
            profile.is_verified = True
            profile.save()
            return JsonResponse({'success': True, 'message': 'Freelance validé avec succès'})
        except FreelanceProfile.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Freelance introuvable'}, status=404)

    if action == 'validate_all_freelances':
        count = FreelanceProfile.objects.filter(is_verified=False).update(is_verified=True)
        return JsonResponse({'success': True, 'message': f'{count} freelance(s) validé(s)'})

    if action == 'suspend_user':
        user_id = data.get('user_id')
        try:
            u = User.objects.get(id=user_id)
            u.is_active = not u.is_active
            u.save()
            status = 'suspendu' if not u.is_active else 'réactivé'
            return JsonResponse({'success': True, 'message': f'Utilisateur {status} avec succès'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Utilisateur introuvable'}, status=404)

    if action == 'resolve_dispute':
        dispute_id = data.get('dispute_id')
        try:
            d = Dispute.objects.get(id=dispute_id)
            d.status = 'resolved'
            d.resolved_at = timezone.now()
            d.resolved_by = request.user
            d.save()
            return JsonResponse({'success': True, 'message': 'Litige résolu'})
        except Dispute.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Litige introuvable'}, status=404)

    if action == 'contact_user':
        recipient_name = data.get('recipient', '').strip()
        subject = data.get('subject', '').strip()
        message_text = data.get('message', '').strip()

        if not recipient_name:
            return JsonResponse({'success': False, 'message': 'Destinataire requis'}, status=400)

        try:
            recipient = User.objects.get(username=recipient_name)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Utilisateur introuvable'}, status=404)

        ContactMessage.objects.create(
            name=request.user.username,
            email=request.user.email,
            subject=subject or 'Message depuis l\'admin',
            message=f"Pour {recipient_name}: {message_text}",
        )

        from chat.models import Thread, Message
        if recipient.role == User.Role.FREELANCE.value:
            thread, _ = Thread.objects.get_or_create(client=request.user, freelance=recipient)
        else:
            thread, _ = Thread.objects.get_or_create(client=recipient, freelance=request.user)
        Message.objects.create(
            thread=thread, sender=request.user,
            text=f"[Admin] {subject}: {message_text}" if subject else f"[Admin] {message_text}"
        )

        return JsonResponse({'success': True, 'message': f'Message envoyé à {recipient_name}'})

    if action == 'create_mission':
        Mission.objects.create(
            client=request.user,
            title=data.get('title', 'Mission'),
            description=data.get('description', ''),
            budget=data.get('budget', 0),
            status='open',
        )
        return JsonResponse({'success': True, 'message': 'Mission créée'})

    if action == 'create_dispute':
        try:
            freelance = User.objects.get(id=data.get('freelance_id'))
            client = User.objects.get(id=data.get('client_id'))
            Dispute.objects.create(
                freelance=freelance,
                client=client,
                reason=data.get('reason', ''),
                amount=data.get('amount', 0),
            )
            return JsonResponse({'success': True, 'message': 'Litige créé'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Utilisateur introuvable'}, status=404)

    if action == 'upload_document':
        recipient_name = data.get('recipient', '').strip()
        subject = data.get('subject', '').strip()
        message_text = data.get('message', '').strip()
        uploaded_file = request.FILES.get('file')

        if not recipient_name:
            return JsonResponse({'success': False, 'message': 'Destinataire requis'}, status=400)
        if not uploaded_file:
            return JsonResponse({'success': False, 'message': 'Fichier requis'}, status=400)

        try:
            recipient = User.objects.get(username=recipient_name)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Utilisateur introuvable'}, status=404)

        Document.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=subject,
            message=message_text,
            file=uploaded_file,
        )

        from chat.models import Thread, Message
        if recipient.role == User.Role.FREELANCE.value:
            thread, _ = Thread.objects.get_or_create(client=request.user, freelance=recipient)
        else:
            thread, _ = Thread.objects.get_or_create(client=recipient, freelance=request.user)
        Message.objects.create(
            thread=thread, sender=request.user,
            text=f"[Admin][Document] {subject or 'Document'} envoyé à {recipient_name}"
        )

        return JsonResponse({'success': True, 'message': f'Document envoyé à {recipient_name}'})

    if action == 'generate_report':
        period = data.get('period', 'Ce mois-ci')
        report_format = data.get('format', 'PDF')

        from django.db.models import Sum
        now = timezone.now()
        if period == 'Ce mois-ci':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'Mois dernier':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == '3 derniers mois':
            start_date = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        txns = Transaction.objects.filter(created_at__gte=start_date)
        total = txns.aggregate(total=Sum('amount'))['total'] or 0
        count = txns.count()
        completed = txns.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
        pending = txns.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

        report_data = {
            'period': period,
            'format': report_format,
            'generated_at': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'total_transactions': count,
            'total_amount': float(total),
            'completed_amount': float(completed),
            'pending_amount': float(pending),
        }

        return JsonResponse({'success': True, 'message': f'Rapport {period} généré', 'report': report_data})

    if action == 'mark_all_read':
        from chat.models import Thread, Message
        admin_threads = request.user.client_threads.all()
        count = 0
        for t in admin_threads:
            cnt = t.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
            count += cnt
        return JsonResponse({'success': True, 'message': f'{count} notification(s) marquée(s) comme lue(s)'})

    if action == 'save_settings':
        from .models import PlatformSettings
        s = PlatformSettings.get_instance()
        bool_fields = ['enable_registrations', 'auto_validate_freelances', 'maintenance_mode',
                       'notif_new_user', 'notif_new_mission', 'notif_payment', 'notif_dispute']
        for key, value in data.items():
            if key in bool_fields:
                setattr(s, key, value in (True, 'True', 'true', 'on', 1, '1'))
            elif hasattr(s, key):
                setattr(s, key, value)
        s.save()
        return JsonResponse({'success': True, 'message': 'Paramètres enregistrés'})

    return JsonResponse({'error': 'Action inconnue'}, status=400)