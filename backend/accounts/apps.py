from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _bootstrap_roles(sender, **kwargs):
    # On exécute init_roles SEULEMENT après toutes les migrations de cette app
    from django.core.management import call_command
    try:
        call_command('init_roles')
    except Exception as e:
        # On logge, mais on ne casse pas le démarrage
        import logging
        logging.getLogger(__name__).exception("init_roles post_migrate failed: %s", e)

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        post_migrate.connect(_bootstrap_roles, sender=self)
