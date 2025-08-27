from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, PermissionsMixin, Permission
from django.db import models

from shared.models import TimeStampedModel


# Create your models here.
class Role(TimeStampedModel):
    nomRole = models.CharField(max_length=255, unique=True, null=False, blank=False)
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True)
    def __str__(self):
        return self.nomRole

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Le champ 'email' est requis")
        if not password:
            raise ValueError("Le champ 'password' est requis")
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Le superuser doit avoir is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True")

        return self.create_user(email, password, **extra_fields)



class CustomUser(AbstractUser, PermissionsMixin,TimeStampedModel):
    username = None
    nom = models.CharField("Nom",max_length=100)
    prenom = models.CharField("Prenom",max_length=100,blank=True,null=True)
    email = models.EmailField("Email",max_length=100, unique=True)
    tel = models.CharField("Telephone",max_length=100)

    role =  models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Role'
    )

    is_staff = models.BooleanField("Staff", default=False)
    is_active = models.BooleanField("Active", default=True)
    is_admin = models.BooleanField("Admin", default=False)

    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom','tel']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    def has_perm(self, perm, obj=None):
        if self.is_superuser:
            return True
        if self.role and self.role.permissions.filter(codename=perm.split('.')[-1]).exists():
            return True
        return super().has_perm(perm, obj)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)



