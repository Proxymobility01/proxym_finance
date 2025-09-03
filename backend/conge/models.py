from django.db import models

from contrat_chauffeur.models import ContratChauffeur
from shared.models import TimeStampedModel


# Create your models here.

class Conge(TimeStampedModel):
    contrat = models.ForeignKey(
        ContratChauffeur, on_delete=models.CASCADE, related_name="conges"
    )
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=50)

    def __str__(self):
        return f"Congé #{self.id} - contrat {self.contrat_id}"

    class Meta:
        db_table = "conge"