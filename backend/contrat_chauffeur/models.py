from __future__ import annotations
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid
from datetime import datetime, timedelta, date  # already imported
from django.utils import timezone
from django.conf import settings

from app_legacy.models import AssociationUserMoto
from shared.models import TimeStampedModel


# ------- Existing battery contract table (read-only mapping) -------
class ContratBatterie(TimeStampedModel):
    reference_contrat = models.CharField(max_length=100, null=True, blank=True)
    montant_total = models.DecimalField(max_digits=14, decimal_places=2)
    montant_paye = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date_signature = models.DateField()
    date_enregistrement = models.DateField()
    date_debut = models.DateField()
    duree_jour = models.IntegerField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)

    statut = models.CharField(max_length=50, null=True, blank=True)

    montant_engage = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    montant_caution = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "contrat_batterie"


    def __str__(self):
        return self.reference_contrat or f"ContratBatterie #{self.pk}"


def contract_upload_path(instance, filename):
    # e.g. contrats/CC-202509-00017/filename.pdf
    ref = instance.reference_contrat or "UNSET"
    return f"contrats/{ref}/{filename}"


class FrequencePaiement(models.TextChoices):
    DAILY = "daily", _("Quotidien")
    WEEKLY = "weekly", _("Hebdomadaire")
    BIWEEKLY = "biweekly", _("Bimensuel")
    MONTHLY = "monthly", _("Mensuel")
    CUSTOM = "custom", _("Personnalisé")


class StatutContrat(models.TextChoices):
    ACTIVE = "active", _("Actif")
    SUSPENDED = "suspended", _("Suspendu")
    TERMINATED = "terminated", _("Résilié")
    COMPLETED = "completed", _("Terminé")


# ---------------- Chauffeur contract (managed by Django) ----------------
class ContratChauffeur(TimeStampedModel):
    reference_contrat = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    montant_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_paye = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)

    frequence_paiement = models.CharField(
        max_length=50,
        choices=FrequencePaiement.choices,
        default=FrequencePaiement.WEEKLY,
    )
    montant_par_paiement = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    date_signature = models.DateField(null=True, blank=True)
    date_enregistrement = models.DateField(null=True, blank=True)
    date_debut = models.DateField(null=True, blank=True)

    # Use days as integer
    duree_jour = models.PositiveIntegerField(null=True, blank=True, help_text=_("Durée du contrat en jours"))
    date_fin = models.DateTimeField(null=True, blank=True)

    statut = models.CharField(max_length=50, choices=StatutContrat.choices, default=StatutContrat.ACTIVE)

    montant_engage = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Physical files (stored as file paths/URLs)
    contrat_physique_chauffeur = models.FileField(upload_to=contract_upload_path, null=True, blank=True)
    contrat_physique_batt = models.FileField(upload_to=contract_upload_path, null=True, blank=True)
    contrat_physique_moto_garant = models.FileField(upload_to=contract_upload_path, null=True, blank=True)
    contrat_physique_batt_garant = models.FileField(upload_to=contract_upload_path, null=True, blank=True)

    # Bloc caution batterie
    montant_caution_batt = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_engage_batt = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    duree_caution_batt = models.DateField(null=True, blank=True)

    # Congés
    jour_conge_total = models.PositiveIntegerField(default=0)
    jour_conge_utilise = models.PositiveIntegerField(default=0)
    jour_conge_restant = models.PositiveIntegerField(default=0, editable=False)

    association_user_moto = models.ForeignKey(
        AssociationUserMoto, on_delete=models.PROTECT, related_name="contrats_chauffeur",
        db_column="association_user_moto_id"
    )

    contrat_batt = models.ForeignKey(
        "contrat_chauffeur.ContratBatterie",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contrats_chauffeur",
    )
    garant = models.ForeignKey(
        "garant.Garant",
        on_delete=models.PROTECT,
        related_name="contrats_chauffeur",
    )
    regle_penalite = models.ForeignKey(
        "penalite.ReglePenalite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contrats_chauffeur",
    )

    class Meta:
        db_table = "contrat_chauffeur"
        indexes = [
            models.Index(fields=["statut", "date_fin"]),
            models.Index(fields=["garant", "statut"]),
            models.Index(fields=["association_user_moto_id", "statut"]),
        ]
        ordering = ("-created",)

    # ---- helpers ----
    @staticmethod
    def _next_reference() -> str:
        """Generate a contract reference like CC-YYYYMM-xxxxx."""
        today = date.today()
        yyyymm = f"{today.year}{today.month:02d}"
        chunk = uuid.uuid4().hex[:5].upper()
        return f"CC-{yyyymm}-{chunk}"

    def clean(self):
        # Numeric guards
        if self.montant_total < 0 or self.montant_paye < 0 or self.montant_engage < 0:
            raise ValidationError(_("Montants négatifs interdits."))
        if self.montant_paye > self.montant_total:
            raise ValidationError(_("Le montant payé ne peut pas dépasser le montant total."))
        if self.montant_engage > self.montant_total:
            raise ValidationError(_("Le montant engagé ne peut pas dépasser le montant total."))
        # Congés
        if self.jour_conge_utilise > self.jour_conge_total:
            raise ValidationError(_("Les congés utilisés ne peuvent pas dépasser le total."))
        # Dates order
        if self.date_signature and self.date_enregistrement and self.date_signature > self.date_enregistrement:
            raise ValidationError(_("La date de signature doit précéder la date d'enregistrement."))
        if self.date_enregistrement and self.date_debut and self.date_enregistrement > self.date_debut:
            raise ValidationError(_("La date d'enregistrement doit précéder la date de début."))
        # AFTER — set midnight of the end day; make aware if USE_TZ
        if self.date_debut and self.duree_jour and not self.date_fin:
            end_date = self.date_debut + timedelta(days=int(self.duree_jour) - 1)
            end_dt = datetime.combine(end_date, datetime.min.time())
            if getattr(settings, "USE_TZ", False) and timezone.is_naive(end_dt):
                end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())
            self.date_fin = end_dt

        # Compute date_fin from duree_jours if needed
        if self.date_debut and self.duree_jour and not self.date_fin:
            self.date_fin = self.date_debut + timedelta(days=int(self.duree_jour) - 1)

    def save(self, *args, **kwargs):
        # Autogen reference if missing
        if not self.reference_contrat:
            self.reference_contrat = self._next_reference()
        # Compute derived fields
        self.montant_restant = max(self.montant_total - self.montant_paye, 0)
        self.jour_conge_restant = max(self.jour_conge_total - self.jour_conge_utilise, 0)
        # Auto set date_enregistrement when moving to ACTIVE
        if self.statut == StatutContrat.ACTIVE and not self.date_enregistrement:
            self.date_enregistrement = date.today()
        self.full_clean()
        return super().save(*args, **kwargs)

    # ---- state transitions (domain guards) ----
    def can_activate(self) -> bool:
        required = [self.garant_id, self.association_user_moto_id, self.date_debut, self.montant_total is not None]
        return self.statut == StatutContrat.DRAFT and all(required)

    def activate(self):
        if not self.can_activate():
            raise ValidationError(_("Conditions non réunies pour activer le contrat."))
        self.statut = StatutContrat.ACTIVE

    def suspend(self):
        if self.statut != StatutContrat.ACTIVE:
            raise ValidationError(_("Seul un contrat actif peut être suspendu."))
        self.statut = StatutContrat.SUSPENDED

    def terminate(self):
        if self.statut not in (StatutContrat.ACTIVE, StatutContrat.SUSPENDED):
            raise ValidationError(_("Seul un contrat actif/suspendu peut être résilié."))
        self.statut = StatutContrat.TERMINATED

    def complete(self):
        if self.montant_restant != 0:
            raise ValidationError(_("Impossible de clôturer: le montant restant n'est pas nul."))
        self.statut = StatutContrat.COMPLETED

    def __str__(self):
        return f"{self.reference_contrat or 'UNSET'} - {self.get_statut_display()}"
