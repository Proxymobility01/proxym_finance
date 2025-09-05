from django.db import models

# Try to import your shared TimeStampedModel; if missing, use a safe fallback
try:
    from shared.models import TimeStampedModel
except Exception:
    class TimeStampedModel(models.Model):
        created = models.DateTimeField(auto_now_add=True)
        updated = models.DateTimeField(auto_now=True)
        class Meta:
            abstract = True


class ContratBatterie(TimeStampedModel):
    reference_contrat = models.CharField(max_length=100, null=True, blank=True)

    montant_total = models.DecimalField(max_digits=14, decimal_places=2)               # NOT NULL
    montant_paye = models.DecimalField(max_digits=14, decimal_places=2, default=0)     # NOT NULL
    montant_restant = models.DecimalField(max_digits=14, decimal_places=2, default=0)  # NOT NULL

    date_signature = models.DateField()        # NOT NULL
    date_enregistrement = models.DateField()   # NOT NULL
    date_debut = models.DateField()            # NOT NULL
    duree_jour = models.IntegerField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)

    statut = models.CharField(max_length=50, null=True, blank=True)

    montant_engage = models.DecimalField(max_digits=14, decimal_places=2)   # NOT NULL
    montant_caution = models.DecimalField(max_digits=14, decimal_places=2)  # NOT NULL

    # Plain integer, matches DB column name 'chauffeur_id_id'
    chauffeur_id = models.IntegerField(db_column="chauffeur_id_id")

    class Meta:
        db_table = "contrat_batterie"
        managed = False  # mapping existing table

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

    # 🔑 Use string references to avoid import-time dependency issues
    association_user_moto = models.ForeignKey(
        "app_legacy.AssociationUserMoto", on_delete=models.PROTECT, related_name="contrats_chauffeur"
    )
    garant = models.ForeignKey(
        "garant.Garant", on_delete=models.PROTECT, related_name="contrats_garantis"
    )
    contrat_batt = models.ForeignKey(
        "contrat_chauffeur.ContratBatterie", on_delete=models.SET_NULL, null=True, blank=True, related_name="contrats_chauffeur"
    )
    # If the 'penalite' app isn’t installed yet, replace this FK with an IntegerField on the same db_column:
    # regle_penalite = models.IntegerField(db_column="regle_penalite_id", null=True, blank=True)
    regle_penalite = models.ForeignKey(
        "penalite.ReglePenalite", on_delete=models.SET_NULL, null=True, blank=True, related_name="contrats"
    )

    class Meta:
        db_table = "contrat_chauffeur"
        managed = False  # mapping existing table

    def __str__(self):
        return self.reference_contrat or f"ContratChauffeur #{self.pk}"
