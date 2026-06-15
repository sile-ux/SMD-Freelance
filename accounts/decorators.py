
from django.shortcuts import redirect
from django.contrib import messages

def freelance_required(view_func):

    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'freelance':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Accès refusé. Cet espace est réservé aux Freelancers.")
        return redirect('dashboard')
    return _wrapped_view

def client_required(view_func):

    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'client':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Accès refusé. Cet espace est réservé aux Clients.")
        return redirect('dashboard')
    return _wrapped_view