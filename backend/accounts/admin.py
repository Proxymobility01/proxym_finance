from django.contrib import admin

# Register your models here.

# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role
from .forms import CustomUserCreationForm, CustomUserChangeForm


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
