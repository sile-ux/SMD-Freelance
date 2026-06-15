from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Contract, Application
from .forms import ContractForm, ApplicationForm
from accounts.decorators import client_required, freelance_required


@login_required
def contract_list(request):

    contracts = Contract.objects.filter(status='OPEN').order_by('-created_at')
    return render(request, 'contracts/contract_list.html', {'contracts': contracts})


@login_required
@client_required
def create_contract(request):

    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.client = request.user
            contract.save()
            messages.success(request, "Votre offre de contrat a été publiée avec succès !")
            return redirect('contract_list')
    else:
        form = ContractForm()
    return render(request, 'contracts/create_contract.html', {'form': form})


@login_required
@freelance_required
def apply_to_contract(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, status='OPEN')

    # Vérifier si le freelance n'a pas déjà postulé
    if Application.objects.filter(contract=contract, freelance=request.user).exists():
        messages.error(request, "Vous avez déjà postulé à ce contrat.")
        return redirect('contract_list')

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.contract = contract
            application.freelance = request.user
            application.save()
            messages.success(request, "Votre candidature a été transmise au client !")
            return redirect('contract_list')
    else:
        form = ApplicationForm()
    return render(request, 'contracts/apply_contract.html', {'form': form, 'contract': contract})