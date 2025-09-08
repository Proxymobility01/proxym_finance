from django.db import models

# Create your models here.
from django.db import models


class Agences(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    class Meta:
        managed = False
        db_table = "users_agences"



class ValidatedUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    class Meta:
        db_table = "validated_users"
        managed = False


class MotoValide(models.Model):
    id = models.BigAutoField(primary_key=True)
    class Meta:
        db_table = "moto_valides"  # adjust if different
        managed = False



class AssociationUserMoto(models.Model):
    id = models.BigAutoField(primary_key=True)
    validated_user = models.ForeignKey(
        ValidatedUser, on_delete=models.DO_NOTHING,
        db_column="validated_user_id", null=True, blank=True
    )
    moto_valide = models.ForeignKey(
        MotoValide, on_delete=models.DO_NOTHING,
        db_column="moto_valide_id", null=True, blank=True
    )
    statut = models.CharField(max_length=50, null=True, blank=True)
    swap_bloque = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = "association_user_motos"  
        managed = False
