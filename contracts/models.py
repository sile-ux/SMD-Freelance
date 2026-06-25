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
    CATEGORY_CHOICES = (
        ('Developpement Web', 'Développement Web'),
        ('Design', 'Design'),
        ('Marketing Digital', 'Marketing Digital'),
        ('Redaction', 'Rédaction'),
        ('Video', 'Vidéo'),
        ('Traduction', 'Traduction'),
        ('Cybersecurite', 'Cybersécurité'),
        ('IA', 'Intelligence Artificielle'),
    )
    LOCATION_CHOICES = (
        ('Teletravail', 'Télétravail'),
        ('Paris', 'Paris'),
        ('Lyon', 'Lyon'),
        ('Marseille', 'Marseille'),
        ('Bordeaux', 'Bordeaux'),
        ('Lille', 'Lille'),
        ('Toulouse', 'Toulouse'),
        ('Nantes', 'Nantes'),
        ('Nice', 'Nice'),
        ('Strasbourg', 'Strasbourg'),
    )
    DURATION_CHOICES = (
        ('1-7 jours', '1-7 jours'),
        ('1-2 semaines', '1-2 semaines'),
        ('1 mois', '1 mois'),
        ('1-3 mois', '1-3 mois'),
        ('3-6 mois', '3-6 mois'),
        ('6+ mois', '6+ mois'),
    )
    PAYMENT_CHOICES = (
        ('fixed', 'Forfait'),
        ('hourly', 'À l\'heure'),
        ('daily', 'À la journée'),
    )
    CURRENCY_CHOICES = (
        ('EUR', '€ EUR'),
        ('USD', '$ USD'),
        ('GBP', '£ GBP'),
        ('XOF', 'FCFA XOF'),
    )
    URGENCY_CHOICES = (
        ('low', 'Normal'),
        ('medium', 'Moyen'),
        ('high', 'Urgent'),
    )
    STATUS_CHOICES = (
        ('open', 'Ouverte'),
        ('in-progress', 'En cours'),
        ('closed', 'Terminée'),
        ('cancelled', 'Annulée'),
    )
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='missions_posted', null=True, blank=True)
    title = models.CharField(max_length=200, verbose_name="Titre de la mission")
    description = models.TextField(verbose_name="Description du besoin")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Developpement Web')
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, default='Teletravail')
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='1 mois')
    budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Budget estimé")
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='fixed')
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='EUR')
    skills_required = models.CharField(max_length=255, help_text="Séparez par des virgules")
    deadline = models.DateField(verbose_name="Date limite", null=True, blank=True)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    extra_info = models.TextField(verbose_name="Infos supplémentaires", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def tag_list(self):
        return [s.strip() for s in self.skills_required.split(',') if s.strip()]

    @property
    def budget_category(self):
        b = float(self.budget)
        if b < 200000:
            return 'small'
        elif b < 500000:
            return 'medium'
        return 'large'

    @property
    def category_slug(self):
        tags = self.tag_list
        return tags[0].lower() if tags else 'general'

    @property
    def badge_text(self):
        from datetime import date, timedelta
        if self.created_at:
            created = self.created_at.date()
            if (date.today() - created).days <= 7:
                return 'Nouveau'
        return dict(self.URGENCY_CHOICES).get(self.urgency, '')

    def __str__(self):
        return self.title


# contracts/models.py

class Application(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='applications', null=True, blank=True)
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='my_applications')

    # MODIFICATION ICI : On autorise temporairement le champ à être vide en base de données
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tarif proposé", null=True,
                                        blank=True)

    cover_letter = models.TextField(verbose_name="Message d'accroche / Motivation", blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'En attente'), ('accepted', 'Acceptée'), ('rejected', 'Refusée')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('mission', 'freelance')
        ordering = ['-created_at']

    def __str__(self):
        return f"Candidature de {self.freelance.username}"