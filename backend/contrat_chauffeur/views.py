from rest_framework import generics
from django.db.models import Q
from .models import ContratBatterie
from .serializers import (
    ContratBatterieListSerializer,
    ContratBatterieDetailSerializer,
    ContratBatterieCreateSerializer,
    ContratBatterieUpdateSerializer,
)

class ContratBatterieListCreateView(generics.ListCreateAPIView):
    queryset = ContratBatterie.objects.all().order_by("-created")

    def get_serializer_class(self):
        return ContratBatterieCreateSerializer if self.request.method == "POST" else ContratBatterieListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        chauffeur_id = self.request.query_params.get("chauffeur_id")
        q = self.request.query_params.get("q")
        if chauffeur_id:
            qs = qs.filter(chauffeur_id=chauffeur_id)
        if q:
            qs = qs.filter(Q(reference_contrat__icontains=q) | Q(statut__icontains=q))
        return qs


class ContratBatterieDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ContratBatterie.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ContratBatterieUpdateSerializer
        return ContratBatterieDetailSerializer
