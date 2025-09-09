from django.db import models

from shared.models import TimeStampedModel


# Create your models here.


class Garant(TimeStampedModel):
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150,null=True,blank=True)
    tel = models.CharField(max_length=50,null=True,blank=True)
    ville = models.CharField(max_length=100,null=True,blank=True)
    quartier = models.CharField(max_length=100, blank=True,null=True)
    photo = models.CharField(max_length=255, blank=True,null=True)
    plan_localisation = models.CharField(max_length=255, blank=True,null=True)
    cni_recto = models.CharField(max_length=255, blank=True,null=True)
    cni_verso = models.CharField(max_length=255, blank=True,null=True)
    justif_activite = models.CharField(max_length=255, blank=True,null=True)
    profession = models.CharField(max_length=150, blank=True,null=True)

    class Meta:
        db_table = "garant"

    def __str__(self):
        return f"{self.nom} {self.prenom}"