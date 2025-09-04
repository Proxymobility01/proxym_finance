from django.conf import settings
from django.db import models

from app_legacy.models import  Agences

from shared.models import TimeStampedModel


# Create your models here.

class ReglePenalite(TimeStampedModel):
    titre = models.CharField(max_length=150, null=True, blank=True)
    heure_min = models.TimeField(null=True, blank=True)
    heure_max = models.TimeField(null=True, blank=True)
    montant_leger_moto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_grave_moto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_leger_batt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_grave_batt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    type_regle = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.titre or f"ReglePenalite #{self.pk}"


class Penalite(TimeStampedModel):
    type_penalite = models.CharField(max_length=100)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_creation = models.DateField()
    motif = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    statut = models.CharField(max_length=50)
    date_payement_manquee = models.DateField(null=True, blank=True)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # String reference to avoid circular import
    contrat_chauffeur = models.ForeignKey(
        "contrat_chauffeur.ContratChauffeur", on_delete=models.CASCADE, related_name="penalites"
    )

    def __str__(self):
        return f"Penalite #{self.id} ({self.type_penalite})"


class PaiementPenalite(TimeStampedModel):
    reference = models.CharField(max_length=100)
    penalite = models.ForeignKey(
        Penalite, on_delete=models.CASCADE, related_name="paiements"
    )
    date_paiement = models.DateTimeField()
    methode_paiement = models.CharField(max_length=50)
    reference_transaction = models.CharField(max_length=100, blank=True)
    employe = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_agence = models.ForeignKey(Agences, on_delete=models.PROTECT, db_column='user_agence_id')

    class Meta:
        db_table = "paiement_penalite"

    def __str__(self):
        return self.reference