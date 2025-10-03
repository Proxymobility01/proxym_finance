# views.py
from rest_framework import serializers, permissions, viewsets
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import CustomUser, Role

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data.update({
            "id": user.id,
            "email": user.email,
            "nom": user.nom,
            "prenom": user.prenom,
            "role": (user.role.nomRole if getattr(user, "role", None) else None),
        })
        return data


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


