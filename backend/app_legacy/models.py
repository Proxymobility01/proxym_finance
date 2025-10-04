from django.db import models

# Create your models here.
from django.db import models


class UsersAgences(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    nom = models.CharField(max_length=255, blank=True, null=True)
    prenom = models.CharField(max_length=255, blank=True, null=True)
    class Meta:
        managed = False
        db_table = "users_agences"

    def __str__(self):
        full = f"{(self.nom or '').strip()} {(self.prenom or '').strip()}".strip()
        return full  or f"Agence {self.id}"



class ValidatedUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_unique_id = models.CharField(max_length=255, blank=True, null=True)  # 👈 ajouté
    nom = models.CharField(max_length=255, blank=True, null=True)
    prenom = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "validated_users"
        managed = False



class MotoValide(models.Model):
    id = models.BigAutoField(primary_key=True)
    moto_unique_id = models.CharField(max_length=255, blank=True, null=True)
    vin = models.CharField(max_length=255, blank=True, null=True) 
    model = models.CharField(max_length=255, blank=True, null=True) 
    gps_imei = models.CharField(max_length=255, blank=True, null=True) 

    class Meta:
        db_table = "motos_valides"  # 👈 attention au vrai nom de ta table
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


    class Meta:
        db_table = "association_user_motos"  
        managed = False


class Agences(models.Model):
    id = models.BigAutoField(primary_key=True)
    nom_agence = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "agences"
        managed = False
