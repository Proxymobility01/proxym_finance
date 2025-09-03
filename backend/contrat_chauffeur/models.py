from django.db import models

from app_legacy.models import AssociationUserMoto
from garant.models import Garant
from shared.models import TimeStampedModel


# Create your models here.


class ContratBatterie(TimeStampedModel):
    reference_contrat = models.CharField(max_length=100, null=True, blank=True)
    montant_total = models.DecimalField(max_digits=14, decimal_places=2)
    montant_paye = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date_signature = models.DateField()
    date_enregistrement = models.DateField()
    date_debut = models.DateField()
    duree_jour = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=50, null=True, blank=True)
    montant_engage = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_caution = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    chauffeur_id = models.ForeignKey(
        AssociationUserMoto, on_delete=models.PROTECT, related_name="contrats_batteries"
    )

    def __str__(self):
        return self.reference_contrat or f"ContratBatterie #{self.pk}"


class ContratChauffeur(TimeStampedModel):
    reference_contrat = models.CharField(max_length=100, null=True, blank=True)
    montant_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    montant_paye = models.DecimalField(max_digits=14, decimal_places=2, default=0, null=True, blank=True)
    montant_restant = models.DecimalField(max_digits=14, decimal_places=2, default=0, null=True, blank=True)
    frequence_paiement = models.CharField(max_length=50, null=True, blank=True)
    montant_par_paiement = models.DecimalField(max_digits=14, decimal_places=2, default=0, null=True, blank=True)
    date_signature = models.DateField(null=True, blank=True)
    date_enregistrement = models.DateField(null=True, blank=True)
    date_debut = models.DateField(null=True, blank=True)
    duree_jour = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=50, null=True, blank=True)

    montant_engage = models.DecimalField(max_digits=14, decimal_places=2, default=0, null=True, blank=True)
    contrat_physique_chauffeur = models.CharField(max_length=255, blank=True, null=True)
    contrat_physique_batt = models.CharField(max_length=255, blank=True, null=True)
    contrat_physique_moto_garant = models.CharField(max_length=255, blank=True, null=True)
    contrat_physique_batt_garant = models.CharField(max_length=255, blank=True, null=True)

    montant_caution_batt = models.DecimalField(max_digits=14, decimal_places=2, default=0, null=True, blank=True)
    montant_engage_batt = models.DecimalField(max_digits=14, decimal_places=2, default=0, null=True, blank=True)
    duree_caution_batt = models.DateField(null=True, blank=True)

    jour_conge_total = models.IntegerField(default=0, null=True, blank=True)
    jour_conge_utilise = models.IntegerField(default=0, null=True, blank=True)
    jour_conge_restant = models.IntegerField(default=0, null=True, blank=True)

    association_user_moto = models.ForeignKey(
        AssociationUserMoto, on_delete=models.PROTECT, related_name="contrats_chauffeur"
    )
    garant = models.ForeignKey(
        Garant, on_delete=models.PROTECT, related_name="contrats_garantis"
    )
    contrat_batt = models.ForeignKey(
        ContratBatterie, on_delete=models.SET_NULL, null=True, blank=True, related_name="contrats_chauffeur"
    )
    # Use string app_label.ModelName to avoid circular import
    regle_penalite = models.ForeignKey(
        "penalite.ReglePenalite", on_delete=models.SET_NULL, null=True, blank=True, related_name="contrats"
    )

    def __str__(self):
        return self.reference_contrat or f"ContratChauffeur #{self.pk}"


