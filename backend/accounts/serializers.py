# views.py
from django.utils import timezone

from rest_framework import serializers, permissions
from accounts.models import CustomUser, Role




# Rôle minimal pour affichage
class RoleLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["nomRole"]

class UserLiteSerializer(serializers.ModelSerializer):
    role = RoleLiteSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "nom",
            "prenom",
            "tel",
            "role",
        ]

# Permission personnalisée : accès seulement pour superuser ou role.nomRole == "Administrateur"
class IsAdminRoleOrSuperuser(permissions.BasePermission):
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return bool(getattr(user, "role", None) and getattr(user.role, "nomRole", "") == "Administrateur")


