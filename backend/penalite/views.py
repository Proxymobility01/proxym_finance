from django.shortcuts import render
from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny

from .models import Penalite, PaiementPenalite
from .serializers import (
    PenaliteListSerializer, PaiementPenaliteCreateSerializer,
)
# Create your views here.
class PenaliteViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    queryset = Penalite.objects.select_related(
        "contrat_chauffeur",
        "contrat_chauffeur__association_user_moto__validated_user",
    ).order_by("-created")
    serializer_class = PenaliteListSerializer



class PaiementPenaliteViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    queryset = (PaiementPenalite.objects
                .select_related("penalite", "penalite__contrat_chauffeur"))
    serializer_class = PaiementPenaliteCreateSerializer