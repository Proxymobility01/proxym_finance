from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from wallet.models import Wallet


class StatutService:
    """
    Service métier responsable de la gestion des statuts des Wallets.
    -----------------------------------------------------------------
    Cette classe isole toute la logique liée au changement d’état d’un Wallet.
    """

    STATUT_MAPPING = {
        "bloquer": "bloque",
        "suspendre": "suspendu",
        "activer": "actif",
    }

    @classmethod
    @transaction.atomic
    def changer_statut(cls, wallet_id: int, action: str) -> Wallet:
        """
        Met à jour le statut d’un Wallet existant.

        Args:
            wallet_id (int): Identifiant du Wallet cible.
            action (str): 'bloquer', 'suspendre' ou 'activer'.

        Returns:
            Wallet: instance mise à jour du modèle Wallet.
        """
        if action not in cls.STATUT_MAPPING:
            raise ValueError(f"Action '{action}' non reconnue. Actions valides : {list(cls.STATUT_MAPPING.keys())}")

        try:
            wallet = Wallet.objects.get(pk=wallet_id)
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist("Le compte wallet spécifié n'existe pas.")

        nouveau_statut = cls.STATUT_MAPPING[action]

        if wallet.statut == nouveau_statut:
            raise ValueError(f"Le compte {wallet.unique_id} est déjà '{nouveau_statut}'.")

        wallet.statut = nouveau_statut
        wallet.save(update_fields=["statut", "updated_at"])
        return wallet
