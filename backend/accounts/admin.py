from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
# Register your models here.

# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role
from .forms import CustomUserCreationForm, CustomUserChangeForm

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

    list_display = ('email', 'nom', 'prenom', 'tel', 'role', 'is_active', 'is_staff', 'is_admin')
    list_filter = ('is_active', 'is_staff', 'is_admin', 'role', 'groups')
    search_fields = ('email', 'nom', 'prenom', 'tel')
    ordering = ('email',)


    fieldsets = (
        (None, {'fields': ('email', 'nom', 'prenom', 'tel','password', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'tel', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('last_login',)

    actions = ["forcer_deconnexion_immediate", "reactiver_utilisateur"]

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
