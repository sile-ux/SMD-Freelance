from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.db import transaction
from .forms import FreelanceRegisterForm, ClientRegisterForm
from .models import User, FreelanceProfile, ClientProfile




def home_view(request):
    return render(request, 'home.html')

def choice_register(request):
    
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/choice_register.html')


@csrf_protect
def register_freelance(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

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
                        title=form.cleaned_data.get('title'),
                        skills=form.cleaned_data.get('skills'),
                        hourly_rate=form.cleaned_data.get('hourly_rate')
                    )

                login(request, user)
                messages.success(request,
                                 "Votre compte Freelance a été créé avec succès ! Il est en attente de validation par l'administrateur.")
                return redirect('dashboard')
            except Exception:
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
                        company_name=form.cleaned_data.get('company_name'),
                        description=form.cleaned_data.get('description')
                    )

                login(request, user)
                messages.success(request, "Votre compte Client a été créé avec succès !")
                return redirect('dashboard')
            except Exception:
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

# Create your views here.
