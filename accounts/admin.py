from django.contrib import admin
from django.contrib import messages
from .models import User, FreelanceProfile, ClientProfile, ContactMessage, Newsletter, Dispute


# Action personnalisée pour valider les profils en masse
@admin.action(description="Approuver et valider les freelancers sélectionnés")
def make_verified(modeladmin, request, queryset):
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(
        request,
        f"Succès : {updated} profil(s) freelancer ont été approuvés et validés.",
        messages.SUCCESS
    )


# Action personnalisée pour suspendre les profils en masse
@admin.action(description="Suspendre / Révoquer les freelancers sélectionnés")
def make_unverified(modeladmin, request, queryset):
    updated = queryset.update(is_verified=False)
    modeladmin.message_user(
        request,
        f"Attention : {updated} profil(s) freelancer ont été suspendus.",
        messages.WARNING
    )


class FreelanceProfileAdmin(admin.ModelAdmin):
    # Colonnes affichées dans le tableau de bord de l'admin
    list_display = ('user', 'title', 'hourly_rate', 'is_verified', 'create_at')

    # Filtres rapides sur le côté droit pour trier par statut de validation
    list_filter = ('is_verified', 'create_at')

    # Barre de recherche pour trouver un freelancer par son nom ou email
    search_fields = ('user__username', 'user__email', 'title')

    # Intégration des actions sécurisées de masse
    actions = [make_verified, make_unverified]


class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    actions = ['mark_as_read']

    @admin.action(description="Marquer comme lus")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)


class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)


# Enregistrement des modèles dans le panneau d'administration
admin.site.register(User)
admin.site.register(ClientProfile)
admin.site.register(FreelanceProfile, FreelanceProfileAdmin)
admin.site.register(ContactMessage, ContactMessageAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(Dispute)