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


class Mission(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='missions_posted', null=True, blank=True)
    title = models.CharField(max_length=200, verbose_name="Titre de la mission")
    description = models.TextField(verbose_name="Description du besoin")
    budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Budget estimé")
    skills_required = models.CharField(max_length=255, help_text="Séparez par des virgules")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# contracts/models.py

class Application(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='applications', null=True, blank=True)
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='my_applications')

    # MODIFICATION ICI : On autorise temporairement le champ à être vide en base de données
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tarif proposé", null=True,
                                        blank=True)

    cover_letter = models.TextField(verbose_name="Message d'accroche / Motivation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('mission', 'freelance')
        ordering = ['-created_at']

    def __str__(self):
        return f"Candidature de {self.freelance.username}"