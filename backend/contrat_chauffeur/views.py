from xml import parsers

from django.db.models import Q
from rest_framework import generics, permissions, viewsets
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from .models import ContratBatterie, ContratChauffeur
from .serializers import (
    ContractBatteryListSerializer,
    ContractBatteryDetailSerializer,
    ContractBatteryCreateSerializer,
    ContractBatteryUpdateSerializer,
    ContractDriverListSerializer,
    ContractDriverDetailSerializer,
    ContractDriverCreateSerializer,
    ContractDriverUpdateSerializer,
)

# -------------------------------------------------------------------
# Battery contracts
# -------------------------------------------------------------------
class ContratBatterieListCreateView(generics.ListCreateAPIView):
    """
    GET: list battery contracts (filters: chauffeur_id, q)
    POST: create battery contract with optional file upload
    """
    queryset = ContratBatterie.objects.all().order_by("-created")
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ContractBatteryCreateSerializer
        return ContractBatteryListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        chauffeur_id = self.request.query_params.get("chauffeur_id")
        q = self.request.query_params.get("q")
        if chauffeur_id:
            qs = qs.filter(chauffeur_id=chauffeur_id)
        if q:
            qs = qs.filter(Q(reference_contrat__icontains=q) | Q(statut__icontains=q))
        return qs

    def perform_create(self, serializer):
        # Handle file upload automatically
        serializer.save()


class ContratBatterieDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: retrieve battery contract
    PUT/PATCH: update battery contract, replacing file if uploaded
    DELETE: delete battery contract and its file
    """
    queryset = ContratBatterie.objects.all()
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ContractBatteryUpdateSerializer
        return ContractBatteryDetailSerializer

    def perform_update(self, serializer):
        instance = self.get_object()
        # Replace file if a new file is uploaded
        new_file = self.request.FILES.get("contrat_physique_batt")
        if new_file and instance.contrat_physique_batt:
            instance.contrat_physique_batt.delete(save=False)
        serializer.save()

    def perform_destroy(self, instance):
        # Delete associated file if exists
        if instance.contrat_physique_batt:
            instance.contrat_physique_batt.delete(save=False)
        instance.delete()


# -------------------------------------------------------------------
# Chauffeur contracts
# -------------------------------------------------------------------
class ContractChauffeurListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/contrats-chauffeurs      -> list
    POST /api/contrats-chauffeurs      -> create (auto-computes date_fin & duree_jour)
    """
    queryset = ContratChauffeur.objects.all().order_by("-created")
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # accept JSON + multipart

    def get_serializer_class(self):
        return ContractDriverCreateSerializer if self.request.method == "POST" else ContractDriverListSerializer


class ContractChauffeurDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/contrats-chauffeurs/<id>  -> retrieve
    PUT    /api/contrats-chauffeurs/<id>  -> update (recomputes date_fin & duree_jour)
    PATCH  /api/contrats-chauffeurs/<id>  -> partial update
    DELETE /api/contrats-chauffeurs/<id>  -> delete
    """
    queryset = ContratChauffeur.objects.all()
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return ContractDriverUpdateSerializer if self.request.method in ("PUT", "PATCH") else ContractDriverDetailSerializer