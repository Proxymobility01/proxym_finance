from django.conf import settings
from django.db import models

from app_legacy.models import UsersAgences
from contrat_chauffeur.models import ContratChauffeur
from shared.models import TimeStampedModel


class PaiementLease(TimeStampedModel):
    reference_paiement = models.CharField(max_length=100, null=True, blank=True)
    montant_moto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_batt = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    methode_paiement = models.CharField(max_length=50)
    reference_transaction = models.CharField(max_length=100, blank=True, null=True)
    type_contrat = models.CharField(max_length=50)

    contrat_chauffeur = models.ForeignKey(
        ContratChauffeur, on_delete=models.CASCADE, related_name="paiements_lease"
    )
    date_concernee = models.DateField()
    date_limite = models.DateField()
    statut = models.CharField(max_length=50)
    employe = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    user_agence = models.ForeignKey(
        UsersAgences,
        on_delete=models.PROTECT,
        db_column='user_agence_id',
        null=True, blank=True
    )

    class Meta:
        db_table = "paiement_lease"
        ordering = ('-created',)

    def __str__(self):
        return self.reference_paiement or f"PaiementLease #{self.pk}"
