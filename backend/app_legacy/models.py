from django.db import models

# Create your models here.
from django.db import models

class AssociationUserMoto(models.Model):
    id = models.IntegerField(primary_key=True)  # adapte selon le vrai type de PK


    class Meta:
        managed = False
        db_table = "association_user_motos"


class Agences(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    class Meta:
        managed = False
        db_table = "users_agences"
