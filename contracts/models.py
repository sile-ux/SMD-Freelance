from django.db import models
from django.conf import settings


class Contract(models.Model):
    STATUS_CHOICES = (
        ('OPEN', 'Ouvert (Postulations possibles)'),
        ('IN_PROGRESS', 'En cours de réalisation'),
        ('COMPLETED', 'Terminé / Livré'),
        ('CANCELLED', 'Annulé'),
    )

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contracts_posted')
    title = models.CharField(max_length=200, verbose_name="Titre de la mission")
    description = models.TextField(verbose_name="Description détaillée du projet")
    budget = models.PositiveIntegerField(verbose_name="Budget proposé (CFA)")
    deadline = models.DateField(verbose_name="Date limite de livraison")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Application(models.Model):
    STATUS_APP = (
        ('PENDING', 'En attente'),
        ('ACCEPTED', 'Acceptée'),
        ('REJECTED', 'Refusée'),
    )

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='applications')
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='my_applications')
    cover_letter = models.TextField(verbose_name="Lettre de motivation / Proposition technique")
    bid_amount = models.PositiveIntegerField(verbose_name="Votre offre tarifaire (CFA)")
    status = models.CharField(max_length=20, choices=STATUS_APP, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.freelance.username} - {self.contract.title}"

class Mission(models.Model):  # <-- Vérifie bien ce nom exact avec la majuscule !
        client = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='missions_posted',
            null=True,
            blank=True
        )
        title = models.CharField(max_length=200, verbose_name="Titre de la mission")
        description = models.TextField(verbose_name="Description du besoin")
        budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Budget estimé")
        skills_required = models.CharField(max_length=255, help_text="Séparez par des virgules")
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return self.title

class Application(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='applications')
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='my_applications')
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tarif proposé (€ ou FCFA)")
    cover_letter = models.TextField(verbose_name="Message d'accroche / Motivation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un freelance ne peut postuler qu'une seule fois à une même mission
        unique_together = ('mission', 'freelance')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.freelance.username} -> {self.mission.title}"