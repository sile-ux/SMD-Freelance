
from django import forms
from django.utils.html import strip_tags
from .models import Contract, Application
from django import forms
from .models import Mission

class QuickMissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['title', 'budget', 'skills_required', 'description']
class BaseSecureForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], str):
                cleaned_data[field] = strip_tags(cleaned_data[field]).strip()
        return cleaned_data

class ContractForm(BaseSecureForm):
    class Meta:
        model = Contract
        fields = ['title', 'description', 'budget', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

class ApplicationForm(BaseSecureForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'bid_amount']