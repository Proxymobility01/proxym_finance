from django.conf import settings
from django.db import models

from app_legacy.models import Agences
from contrat_chauffeur.models import ContratChauffeur
from shared.models import TimeStampedModel


class PaiementLease(TimeStampedModel):
    reference_paiement = models.CharField(max_length=100, null=True, blank=True)
    montant_moto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_batt = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date_paiement = models.DateField()
    methode_paiement = models.CharField(max_length=50)
    reference_transaction = models.CharField(max_length=100, blank=True, null=True)
    type_contrat = models.CharField(max_length=50)

    contrat_chauffeur = models.ForeignKey(
        ContratChauffeur, on_delete=models.CASCADE, related_name="paiements_lease"
    )
    date_concernee = models.DateTimeField()
    date_limite = models.DateTimeField()
    statut = models.CharField(max_length=50)

    employe = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    user_agence = models.ForeignKey(
        Agences,
        on_delete=models.PROTECT,
        db_column='user_agence_id',
        null=True, blank=True
    )

    class Meta:
        db_table = "paiement_lease"

    def __str__(self):
        return self.reference_paiement or f"PaiementLease #{self.pk}"
