from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Permission
from django.core.management import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from accounts.models import Role


class Command(BaseCommand):
    help = 'Initialize roles'

    def handle(self, *args, **kwargs):
        # Recreation automatique des permissions manquantes
        for app_config in apps.get_app_configs():
            create_permissions(app_config,verbosity=0,using=DEFAULT_DB_ALIAS)
        roles ={
            "GestionnaireFinancier":{
                "permissions":[]
            },

            "Administrateur":{
                "permissions": "__all__"
            }
        }

        for nom, config in roles.items():
            role,created = Role.objects.get_or_create(nomRole=nom)
            perms = []

            if config["permissions"] == "__all__":
                perms = Permission.objects.all()
            else:
                for code in config["permissions"]:
                    matching_perms = Permission.objects.filter(codename=code)
                    if not matching_perms.exists():
                        self.stdout.write(self.style.WARNING(f"⚠️ Permission '{code}' introuvable."))
                    elif matching_perms.count() > 1:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Permission '{code}' dupliquée ({matching_perms.count()} fois). Ignorée."))
                    else:
                        perms.append(matching_perms.first())

            role.permissions.set(perms)
            role.save()

            action = "create" if created else "update"
            self.stdout.write(self.style.SUCCESS(f"✅ Rôle '{nom}' {action} avec {len(perms)} permissions."))
