from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _

from django.conf import settings
from django.db import models

from app_legacy.models import  UsersAgences

from shared.models import TimeStampedModel


# Create your models here.

class StatutPenalite(models.TextChoices):
    NON_PAYE = "non_paye", _("Non payé")
    PARTIELLEMENT_PAYE = "partiellement_paye", _("Partiellement payé")
    PAYE = "paye", _("Payé")
    ANNULEE = "annulee", _("Annulée")


class TypePenalite(models.TextChoices):
    LEGERE = "legere", _("Légère")
    GRAVE  = "grave",  _("Grave")


class Penalite(TimeStampedModel):
    type_penalite = models.CharField(max_length=100, choices=TypePenalite.choices)
    montant_penalite = models.DecimalField(max_digits=12, decimal_places=2)
    motif_penalite = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    statut_penalite = models.CharField(max_length=50,choices=StatutPenalite.choices,default=StatutPenalite.NON_PAYE)
    date_paiement_manquee = models.DateField(null=True, blank=True)
    date_limite_reference = models.DateField(null=True, blank=True)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    echeance_paiement_penalite = models.DateTimeField(null=True, blank=True)
    justificatif_annulation = models.TextField(blank=True, default="")
    annulee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="penalites_annulees",
    )
    date_annulation = models.DateTimeField(null=True, blank=True)

    contrat_chauffeur = models.ForeignKey(
        "contrat_chauffeur.ContratChauffeur", on_delete=models.CASCADE, related_name="penalites"
    )

    class Meta:
        ordering = ('-created',)
        db_table = "penalite"

        constraints = [
            # Empêche les doublons de pénalité pour un même contrat, un même jour et un même type (12h vs 14h)
            models.UniqueConstraint(
                fields=["contrat_chauffeur", "date_paiement_manquee", "type_penalite"],
                name="uniq_penalite_par_contrat_jour_et_type",
            ),
            models.CheckConstraint(
                name="penalite_annulee_uniquement_si_legere",
                check=(~Q(statut_penalite=StatutPenalite.ANNULEE) | Q(type_penalite=TypePenalite.LEGERE)),
            ),
            models.CheckConstraint(
                name="penalite_annulee_justificatif_obligatoire",
                check=(~Q(statut_penalite=StatutPenalite.ANNULEE) | ~Q(justificatif_annulation="")),
            ),
            models.CheckConstraint(
                name="penalite_annulee_montant_paye_zero",
                check=(~Q(statut_penalite=StatutPenalite.ANNULEE) | Q(montant_paye=0)),
            ),

        ]

    def __str__(self):
        return f"Penalite #{self.id} ({self.type_penalite})"

    def save(self, *args, **kwargs):
        if self.statut_penalite == StatutPenalite.ANNULEE:
            self.montant_restant = 0
            self.echeance_paiement_penalite = None
        else:
            self.montant_restant = max(self.montant_penalite - self.montant_paye, 0)
        super().save(*args, **kwargs)



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

    class Meta:
        db_table = "penalite_regle"
    def __str__(self):
        return self.titre or f"ReglePenalite #{self.pk}"



class PaiementPenalite(TimeStampedModel):
    reference = models.CharField(max_length=100)
    penalite = models.ForeignKey(
        Penalite, on_delete=models.CASCADE, related_name="paiements"
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    methode_paiement = models.CharField(max_length=50)
    reference_transaction = models.CharField(max_length=100, blank=True,null=True)
    employe = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=True, blank=True)
    user_agence = models.ForeignKey(UsersAgences, on_delete=models.PROTECT, db_column='user_agence_id', null=True, blank=True)

    class Meta:
        db_table = "paiement_penalite"

    def __str__(self):
        return self.reference