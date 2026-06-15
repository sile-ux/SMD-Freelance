# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from .forms import FreelanceRegisterForm, ClientRegisterForm
from .models import User, FreelanceProfile, ClientProfile
from contracts.models import Mission
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
        form = QuickMissionForm(request.POST)
        if form.is_valid():
            if not request.user.is_authenticated:
                request.session['pending_mission'] = form.cleaned_data
                messages.info(request, "Mission configurée ! Créez votre compte pour la mettre en ligne.")
                return redirect('register_client')
            else:
                mission = form.save(commit=False)
                mission.client = request.user
                mission.save()
                messages.success(request, "Votre mission a été publiée avec succès !")
                return redirect('home')
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
                return redirect('login')
            except Exception as e:
                print(f"❌ ERREUR SCRIPT FREELANCE: {e}")
                messages.error(request, "Une erreur est survenue lors de la création de votre profil.")
    else:
        form = FreelanceRegisterForm()
    return render(request, 'accounts/register_freelance.html', {'form': form})


@csrf_protect
def register_client(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

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
                return redirect('dashboard')
            except Exception as e:
                print(f"❌ ERREUR SCRIPT CLIENT : {e}")
                messages.error(request, "Une erreur est survenue lors de la création de votre profil.")
    else:
        form = ClientRegisterForm()
    return render(request, 'accounts/register_client.html', {'form': form})


@csrf_protect
def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username_input = request.POST.get('username')
        password_input = request.POST.get('password')
        user = authenticate(request, username=username_input, password=password_input)
        if user is not None:
            login(request, user)
            messages.success(request, f"Bon retour, {user.username} !")
            return redirect('dashboard')
        else:
            messages.error(request, "Identifiants invalides.")
    return render(request, 'accounts/login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN.value:
        return redirect('/admin/')
    elif user.role == User.Role.FREELANCE.value:
        return render(request, 'accounts/dashboard_freelance.html', {'profile': user.freelance_profile})
    elif user.role == User.Role.CLIENT.value:
        return render(request, 'accounts/dashboard_client.html', {'profile': user.client_profile})
    return redirect('choice_register')


def choice_register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/choice_register.html')