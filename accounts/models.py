# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        FREELANCE = 'FREELANCE', 'Freelancer'
        CLIENT = 'CLIENT', 'Particulier/Entreprise'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT.value
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

class FreelanceProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='freelance_profile')
    title = models.CharField(max_length=100, help_text='ex: développeur fullstack python')
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=250, help_text="compétences séparées par des virgules")
    portfolio_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="tarif horaire indicatif")
    is_verified = models.BooleanField(default=False)
    specialty = models.CharField(max_length=100, blank=True, null=True)
    experience_level = models.CharField(max_length=20, default='intermediate',
        choices=[('junior', 'Junior'), ('intermediate', 'Intermédiaire'), ('senior', 'Senior')])
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    # Notifications
    notif_email = models.BooleanField(default=True)
    notif_push = models.BooleanField(default=True)
    notif_missions = models.BooleanField(default=False)
    notif_messages = models.BooleanField(default=True)
    notif_reminders = models.BooleanField(default=False)
    # Privacy
    profile_public = models.BooleanField(default=True)
    share_email = models.BooleanField(default=False)
    # Appearance
    theme = models.CharField(max_length=20, default='Clair')
    language = models.CharField(max_length=20, default='Français')
    font_size = models.CharField(max_length=20, default='Normale')
    # Preferences
    preferred_categories = models.CharField(max_length=100, default='Toutes')
    min_budget = models.CharField(max_length=100, default='Aucun')
    auto_alerts = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"profile Freelance de {self.user.username}"

    @property
    def skill_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def full_stars(self):
        return int(self.rating) if self.rating else 0

    @property
    def online_status(self):
        from datetime import timedelta
        from django.utils import timezone
        if self.user.last_login and (timezone.now() - self.user.last_login) < timedelta(minutes=5):
            return 'online'
        return 'offline'

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    compagny_name = models.CharField(max_length=100, blank=True, null=True, help_text='laissez vide si particulier')
    description = models.TextField(blank=True)
    website = models.URLField(blank=True, null=True)
    # Notifications
    notif_email = models.BooleanField(default=True)
    notif_push = models.BooleanField(default=True)
    notif_missions = models.BooleanField(default=False)
    notif_messages = models.BooleanField(default=True)
    notif_reminders = models.BooleanField(default=False)
    # Privacy
    profile_public = models.BooleanField(default=True)
    share_email = models.BooleanField(default=False)
    # Appearance
    theme = models.CharField(max_length=20, default='Clair')
    language = models.CharField(max_length=20, default='Français')
    font_size = models.CharField(max_length=20, default='Normale')
    # Preferences
    preferred_categories = models.CharField(max_length=100, default='Toutes')
    min_budget = models.CharField(max_length=100, default='Aucun')
    auto_alerts = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)

    @property
    def bio(self):
        return self.description

    def __str__(self):
        return f"profile client de {self.user.username}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message de {self.name} — {self.subject or 'Sans sujet'}"


class Newsletter(models.Model):
    email = models.EmailField(max_length=191, unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet {self.user.username}: {self.balance} CFA"


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('deposit', 'Dépôt'),
        ('mission_payment', 'Paiement mission'),
        ('withdrawal', 'Retrait'),
        ('refund', 'Remboursement'),
        ('transfer', 'Virement interne'),
    )
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    )
    METHOD_CHOICES = (
        ('orange', 'Orange Money'),
        ('wave', 'Wave'),
        ('mtn', 'MTN Mobile Money'),
        ('stripe', 'Carte bancaire'),
        ('bank', 'Virement bancaire'),
        ('wallet', 'Portefeuille SMD-Tech'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=50, unique=True, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    account = models.CharField(max_length=100, blank=True)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    freelance = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transactions')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            prefix = {'deposit': 'DEP', 'mission_payment': 'MISS', 'withdrawal': 'WDR',
                      'refund': 'RFD', 'transfer': 'TRF'}.get(self.type, 'TXN')
            import random, string
            self.reference = f"#{prefix}-{''.join(random.choices(string.digits, k=6))}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.get_type_display()} — {self.amount} CFA"


class Dispute(models.Model):
    STATUS_CHOICES = (
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolu'),
    )
    freelance = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_as_freelance')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_as_client')
    mission = models.ForeignKey('contracts.Mission', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputes_resolved')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Litige {self.freelance.username} vs {self.client.username} — {self.get_status_display()}"


class Document(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_documents')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_documents')
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document de {self.sender.username} à {self.recipient.username} — {self.file.name}"


class PlatformSettings(models.Model):
    # Général
    site_name = models.CharField(max_length=100, default='CMD-FREELANCE')
    site_description = models.TextField(blank=True, default='Plateforme de mise en relation freelances et clients')
    support_email = models.EmailField(default='support@cmd-freelance.com')
    default_currency = models.CharField(max_length=10, default='FCFA')

    # Commissions & Finances
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
        help_text='Commission plateforme en %')
    min_payout = models.DecimalField(max_digits=12, decimal_places=2, default=5000,
        help_text='Montant minimum de retrait (FCFA)')
    max_payout = models.DecimalField(max_digits=12, decimal_places=2, default=5000000,
        help_text='Montant maximum de retrait (FCFA)')

    # Inscriptions & Modération
    enable_registrations = models.BooleanField(default=True, verbose_name='Activer les inscriptions')
    auto_validate_freelances = models.BooleanField(default=False,
        verbose_name='Valider automatiquement les freelances')
    maintenance_mode = models.BooleanField(default=False, verbose_name='Mode maintenance')

    # Notifications admin
    notif_new_user = models.BooleanField(default=True, verbose_name='Nouvelle inscription')
    notif_new_mission = models.BooleanField(default=True, verbose_name='Nouvelle mission')
    notif_payment = models.BooleanField(default=True, verbose_name='Paiement reçu')
    notif_dispute = models.BooleanField(default=True, verbose_name='Nouveau litige')

    # Réseaux sociaux
    facebook_url = models.URLField(blank=True, default='')
    twitter_url = models.URLField(blank=True, default='')
    linkedin_url = models.URLField(blank=True, default='')

    # SEO
    meta_keywords = models.CharField(max_length=300, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paramètres plateforme'
        verbose_name_plural = 'Paramètres plateforme'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Paramètres plateforme — {self.site_name}"