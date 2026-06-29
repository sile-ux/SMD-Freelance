from django import forms
from django.utils.html import strip_tags
from .models import Contract, Application, Mission


class QuickMissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = [
            'title', 'description', 'category', 'location', 'duration',
            'budget_type', 'budget', 'payment_type', 'currency', 'skills_required',
            'deadline', 'urgency', 'extra_info',
        ]
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'extra_info': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        budget_type = cleaned_data.get('budget_type')
        budget = cleaned_data.get('budget')
        if budget_type == 'negotiable':
            cleaned_data['budget'] = None
        elif not budget:
            self.add_error('budget', 'Veuillez entrer un budget ou sélectionner "À discuter".')
        return cleaned_data

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