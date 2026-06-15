from django import forms
from django.utils.html import strip_tags
from .models import Contract, Application, Mission

# Formulaire pour la publication rapide depuis la page d'accueil
class QuickMissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['title', 'budget', 'skills_required', 'description']

# Classe parente de sécurité pour nettoyer les failles XSS (balises HTML)
class BaseSecureForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], str):
                cleaned_data[field] = strip_tags(cleaned_data[field]).strip()
        return cleaned_data

# Formulaire pour les contrats standards
class ContractForm(BaseSecureForm):
    class Meta:
        model = Contract
        fields = ['title', 'description', 'budget', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

# CORRECTION ICI : Formulaire pour les candidatures des Freelances
class ApplicationForm(BaseSecureForm):
    class Meta:
        model = Application
        # Remplacement de 'bid_amount' par 'proposed_rate' pour s'aligner avec ton modèle
        fields = ['cover_letter', 'proposed_rate']