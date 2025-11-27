from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import CustomUser, Role
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .service import sync_user_with_auth_service

User = get_user_model()


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nomRole',)
    search_fields = ('nomRole',)
    filter_horizontal = ('permissions',)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    # ✅ AJOUT : 'auth_user_id_central' pour voir le lien ID Auth Service
    list_display = ('email', 'nom', 'prenom', 'tel', 'role', 'auth_user_id_central', 'is_active', 'is_staff',
                    'is_admin')

    list_filter = ('is_active', 'is_staff', 'is_admin', 'role', 'groups')
    search_fields = ('email', 'nom', 'prenom', 'tel')
    ordering = ('email',)

    # ✅ AJOUT : 'auth_user_id_central' en lecture seule
    readonly_fields = ('last_login', 'auth_user_id_central')

    fieldsets = (
        (None, {'fields': ('email', 'nom', 'prenom', 'tel', 'password', 'role')}),
        # ✅ AJOUT : Une section pour voir l'état de la synchro
        ('Synchronisation Auth Service', {'fields': ('auth_user_id_central',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'tel', 'role', 'password1', 'password2'),
        }),
    )

    actions = ["forcer_deconnexion_immediate", "reactiver_utilisateur"]

    # --- LOGIQUE DE SYNCHRONISATION ---

    def save_model(self, request, obj, form, change):
        """
        Surcharge de la sauvegarde pour déclencher la synchronisation
        avec l'Auth Service (Microservice Central).
        """
        # 1. Sauvegarde locale (MySQL Finance)
        super().save_model(request, obj, form, change)

        # 2. Récupération du mot de passe brut (Uniquement lors de la création)
        raw_password = None
        if not change:
            # CustomUserCreationForm stocke le mdp dans password1
            raw_password = form.cleaned_data.get('password1')

        # 3. Appel du service de synchronisation
        # Cela envoie une requête HTTP à l'Auth Service
        success, msg = sync_user_with_auth_service(obj, raw_password)

        # 4. Feedback visuel à l'admin
        if success:
            self.message_user(request, f"✅ Synchro Auth Service réussie : {msg}", messages.SUCCESS)
        else:
            # On met un WARNING car l'user est créé localement mais pas distant
            self.message_user(request, f"⚠️ Sauvegardé localement MAIS échec synchro Auth Service : {msg}",
                              messages.WARNING)

    # --- ACTIONS PERSONNALISÉES (Inchangées) ---

    def forcer_deconnexion_immediate(self, request, queryset):
        total_blacklisted = 0
        for user in queryset:
            # 1) Blacklister tous les refresh tokens connus
            for t in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=t)
                total_blacklisted += 1
            # 2) Désactiver le compte => effet immédiat (401 sur n'importe quelle requête)
            if user.is_active:
                user.is_active = False
                user.save(update_fields=["is_active"])
        self.message_user(
            request,
            f"Déconnexion forcée : {total_blacklisted} token(s) blacklistés et compte(s) désactivé(s).",
            messages.SUCCESS,
        )

    forcer_deconnexion_immediate.short_description = "🔒 Forcer la déconnexion (immédiat)"

    def reactiver_utilisateur(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} compte(s) ré-activé(s).", messages.SUCCESS)

    reactiver_utilisateur.short_description = "✅ Réactiver l'utilisateur"