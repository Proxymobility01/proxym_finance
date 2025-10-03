# accounts/management/commands/init_roles.py
from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Permission
from django.core.management import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from accounts.models import Role


class Command(BaseCommand):
    help = 'Initialize roles'

    def handle(self, *args, **kwargs):
        # (1) S'assurer que toutes les permissions existent
        for app_config in apps.get_app_configs():
            create_permissions(app_config, verbosity=0, using=DEFAULT_DB_ALIAS)

        # (2) Définition des rôles
        roles = {
            # 👉 les deux rôles ont TOUTES les permissions
            "GestionnaireFinancier": {"permissions": "__all__"},
            "Administrateur":        {"permissions": "__all__"},
        }

        # (3) Attribution
        for nom, config in roles.items():
            role, created = Role.objects.get_or_create(nomRole=nom)

            if config["permissions"] == "__all__":
                perms = Permission.objects.all()
            else:
                perms = Permission.objects.filter(codename__in=config["permissions"])

            role.permissions.set(perms)
            role.save()

            action = "créé" if created else "mis à jour"
            self.stdout.write(self.style.SUCCESS(
                f"✅ Rôle '{nom}' {action} avec {perms.count()} permissions."
            ))
