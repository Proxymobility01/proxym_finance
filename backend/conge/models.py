from django.utils.translation import gettext_lazy as _
from django.db import models
from contrat_chauffeur.models import ContratChauffeur
from shared.models import TimeStampedModel

class StatutConge(models.TextChoices):
    ANNULE    = "annule", _("Annulé")
    EN_ATTENTE= "en_attente", _("En attente")
    APPROUVE  = "approuve", _("Approuvé")
    TERMINE   = "termine", _("Terminé")
    REJETE    = "rejete", _("Rejeté")
# Create your models here.

class Conge(TimeStampedModel):
    contrat = models.ForeignKey(
        ContratChauffeur, on_delete=models.CASCADE, related_name="conges"
    )
    date_debut = models.DateTimeField(null=True)
    date_fin = models.DateTimeField(null=True)
    date_reprise = models.DateTimeField(null=True)
    nb_jour = models.IntegerField(default=0)
    statut = models.CharField(max_length=50,choices=StatutConge.choices,
        default=StatutConge.EN_ATTENTE )
    motif_conge = models.CharField(max_length=500,null=True, blank=True)

    def __str__(self):
        return f"Congé #{self.id} - contrat {self.contrat_id}"

    class Meta:
        db_table = "conge"
        ordering = ("-created",)