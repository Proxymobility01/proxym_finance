from django.shortcuts import render

# Create your views here.
# conge/views.py

from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from .models import Conge
from .serializers import CongeCreateSerializer, CongeUpdateSerializer, CongeBaseSerializer

class CongeViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Conge.objects.all().select_related(
        "contrat", "contrat__association_user_moto__validated_user"
    )

    def get_serializer_class(self):
        if self.action == "create":
            return CongeCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CongeUpdateSerializer
        return CongeBaseSerializer
