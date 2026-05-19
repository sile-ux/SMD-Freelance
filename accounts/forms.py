from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from .models import User, FreelanceProfile, ClientProfile


class BaseSecureForm(forms.ModelForm):


    def clean(self):
        cleaned_data = super().clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], str):

                cleaned_data[field] = strip_tags(cleaned_data[field]).strip()
        return cleaned_data


class FreelanceRegisterForm(BaseSecureForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 text-sm'}),
                               label="Mot de passe")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 text-sm'}),
                                       label="Confirmer le mot de passe")

    title = forms.CharField(max_length=100, label="Titre professionnel (ex: Développeur Django)")
    skills = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Compétences (séparez par des virgules)")
    hourly_rate = forms.IntegerField(label="Tarif horaire (CFA / heure)")

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number']

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        return confirm_password


class ClientRegisterForm(BaseSecureForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-gray-800 text-sm'}),
                               label="Mot de passe")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-gray-800 text-sm'}),
                                       label="Confirmer le mot de passe")


    company_name = forms.CharField(max_length=100, required=False, label="Nom de l'entreprise (Optionnel)")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False,
                                  label="Description de vos besoins ou de votre activité")

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number']

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        return confirm_password