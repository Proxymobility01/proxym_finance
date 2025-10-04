from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import connection
import logging


def _bootstrap_roles(sender, **kwargs):
    from django.core.management import call_command

    try:
        # Vérifie si la table accounts_role existe
        if 'accounts_role' in connection.introspection.table_names():
            call_command('init_roles')
        else:
            logging.getLogger(__name__).warning(
                "init_roles ignoré : la table accounts_role n'existe pas encore."
            )
    except Exception as e:
        # On logge l'erreur mais on ne casse pas le démarrage
        logging.getLogger(__name__).exception(
            "init_roles post_migrate failed: %s", e
        )


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        post_migrate.connect(_bootstrap_roles, sender=self)
