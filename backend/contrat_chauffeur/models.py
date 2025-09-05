from django.db import models

from app_legacy.models import AssociationUserMoto
from garant.models import Garant
from shared.models import TimeStampedModel
from django.db import models
from django.core.exceptions import ValidationError
from app_legacy.models import AssociationUserMoto
from garant.models import Garant


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

    class Meta:
        db_table = "contrat_batterie"

    def __str__(self):
        return self.reference_contrat or f"ContratBatterie #{self.pk}"





FREQ_CHOICES = ("daily", "weekly", "monthly")
STATUS_CHOICES = ("DRAFT", "ACTIVE", "SUSPENDED", "TERMINATED", "COMPLETED")

class ContratChauffeur(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    reference_contrat = models.CharField(max_length=100, null=True, blank=True)
    montant_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    montant_paye = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    montant_restant = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    frequence_paiement = models.CharField(max_length=50, null=True, blank=True)
    montant_par_paiement = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    date_signature = models.DateField(null=True, blank=True)
    date_enregistrement = models.DateField(null=True, blank=True)
    date_debut = models.DateField(null=True, blank=True)
    duree_jour = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)

    statut = models.CharField(max_length=50, null=True, blank=True)

    montant_engage = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    contrat_physique_chauffeur = models.CharField(max_length=255, null=True, blank=True)
    contrat_physique_batt = models.CharField(max_length=255, null=True, blank=True)
    contrat_physique_moto_garant = models.CharField(max_length=255, null=True, blank=True)
    contrat_physique_batt_garant = models.CharField(max_length=255, null=True, blank=True)

    montant_caution_batt = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    montant_engage_batt = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    duree_caution_batt = models.DateField(null=True, blank=True)

    jour_conge_total = models.IntegerField(null=True, blank=True)
    jour_conge_utilise = models.IntegerField(null=True, blank=True)
    jour_conge_restant = models.IntegerField(null=True, blank=True)

    association_user_moto = models.ForeignKey(
        AssociationUserMoto, on_delete=models.DO_NOTHING, db_column="association_user_moto_id"
    )
    contrat_batt_id = models.BigIntegerField(null=True, blank=True)
    garant = models.ForeignKey(Garant, on_delete=models.DO_NOTHING, db_column="garant_id")
    regle_penalite_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "contract_chauffeur"  # change if your table name differs
        managed = False

    def clean(self):
        if self.frequence_paiement and self.frequence_paiement.lower() not in FREQ_CHOICES:
            raise ValidationError({"frequence_paiement": f"Must be one of {FREQ_CHOICES}."})

        if self.statut and self.statut.upper() not in STATUS_CHOICES:
            raise ValidationError({"statut": f"Must be one of {STATUS_CHOICES}."})

        # enforce: only 1 ACTIVE contract per association
        if (self.statut or "").upper() == "ACTIVE":
            qs = ContractChauffeur.objects.filter(
                association_user_moto_id=self.association_user_moto_id,
                statut__iexact="ACTIVE",
            )
            if self.pk: qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("An ACTIVE contract already exists for this association_user_moto.")


    def __str__(self):
        return self.reference_contrat or f"ContratChauffeur #{self.pk}"


