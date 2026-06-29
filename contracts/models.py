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
    BUDGET_TYPE_CHOICES = (
        ('fixed', 'Budget fixe'),
        ('negotiable', 'À discuter'),
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
    budget_type = models.CharField(max_length=20, choices=BUDGET_TYPE_CHOICES, default='fixed')
    budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Budget estimé", null=True, blank=True)
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
        if self.budget is None:
            return 'negotiable'
        b = float(self.budget)
        if b < 200000:
            return 'small'
        elif b < 500000:
            return 'medium'
        return 'large'

    @property
    def budget_display(self):
        if self.budget_type == 'negotiable' or self.budget is None:
            return 'À discuter'
        return f"{float(self.budget):,.0f} CFA"

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


class Devis(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('accepted', 'Accepté'),
        ('rejected', 'Refusé'),
        ('cancelled', 'Annulé'),
    )
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devis_sent')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='devis_received')
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True, related_name='devis')
    mission = models.ForeignKey(Mission, on_delete=models.SET_NULL, null=True, blank=True, related_name='devis')

    ref = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    client_name = models.CharField(max_length=200, verbose_name="Nom du client")
    client_email = models.EmailField(verbose_name="Email du client")
    client_company = models.CharField(max_length=200, blank=True, verbose_name="Entreprise")
    client_phone = models.CharField(max_length=50, blank=True, verbose_name="Téléphone")

    description = models.TextField(verbose_name="Description de la prestation")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Montant estimé HT")
    tva = models.DecimalField(max_digits=5, decimal_places=2, default=18, verbose_name="TVA (%)")

    freelance_company = models.CharField(max_length=200, blank=True, verbose_name="Votre entreprise")
    freelance_phone = models.CharField(max_length=50, blank=True, verbose_name="Votre téléphone")
    freelance_address = models.TextField(blank=True, verbose_name="Votre adresse")
    freelance_siret = models.CharField(max_length=50, blank=True, verbose_name="N° SIRET / RC")

    issue_date = models.DateField(verbose_name="Date d'émission")
    valid_until = models.DateField(verbose_name="Validité du devis", null=True, blank=True)

    terms = models.TextField(blank=True, verbose_name="Conditions", default="Devis valable 30 jours")
    notes = models.TextField(blank=True, verbose_name="Notes supplémentaires")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Devis"
        verbose_name_plural = "Devis"

    @property
    def total_ht(self):
        return float(self.amount)

    @property
    def tva_amount(self):
        return float(self.amount) * float(self.tva) / 100

    @property
    def total_ttc(self):
        return self.total_ht + self.tva_amount

    def save(self, *args, **kwargs):
        if not self.ref:
            from django.utils import timezone
            year = timezone.now().year
            count = Devis.objects.filter(freelance=self.freelance).count() + 1
            self.ref = f"DEV-{year}-{str(count).zfill(3)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ref} — {self.client_name}"


class Invoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('paid', 'Payée'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulée'),
    )
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    mission = models.ForeignKey(Mission, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    ref = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    client_name = models.CharField(max_length=200)
    client_email = models.EmailField()
    client_company = models.CharField(max_length=200, blank=True, verbose_name="Entreprise du client")
    client_address = models.TextField(blank=True, verbose_name="Adresse du client")
    client_phone = models.CharField(max_length=50, blank=True, verbose_name="Téléphone du client")

    description = models.TextField(verbose_name="Description de la prestation")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Montant HT")
    tva = models.DecimalField(max_digits=5, decimal_places=2, default=18, verbose_name="TVA (%)")

    freelance_company = models.CharField(max_length=200, blank=True, verbose_name="Nom de votre entreprise")
    freelance_address = models.TextField(blank=True, verbose_name="Votre adresse")
    freelance_phone = models.CharField(max_length=50, blank=True, verbose_name="Votre téléphone")
    freelance_siret = models.CharField(max_length=50, blank=True, verbose_name="N° SIRET / Registre de commerce")

    issue_date = models.DateField(verbose_name="Date d'émission")
    due_date = models.DateField(verbose_name="Date d'échéance")

    terms = models.TextField(blank=True, verbose_name="Conditions de paiement",
                             default="Paiement à réception sous 30 jours")
    notes = models.TextField(blank=True, verbose_name="Notes supplémentaires")

    bank_name = models.CharField(max_length=200, blank=True, verbose_name="Banque")
    bank_iban = models.CharField(max_length=50, blank=True, verbose_name="IBAN")
    bank_bic = models.CharField(max_length=50, blank=True, verbose_name="BIC/SWIFT")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_ht(self):
        return float(self.amount)

    @property
    def tva_amount(self):
        return float(self.amount) * float(self.tva) / 100

    @property
    def total_ttc(self):
        return self.total_ht + self.tva_amount

    def save(self, *args, **kwargs):
        if not self.ref:
            from django.utils import timezone
            year = timezone.now().year
            count = Invoice.objects.filter(freelance=self.freelance).count() + 1
            self.ref = f"FAC-{year}-{str(count).zfill(3)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ref} — {self.client_name}"