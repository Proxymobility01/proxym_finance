from django.db.models import Q
from rest_framework import generics
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from .models import ContratBatterie, ContratChauffeur
from .serializers import (
    ContractBatteryListSerializer,
    ContractBatteryDetailSerializer,
    ContractBatteryCreateSerializer,
    ContractBatteryUpdateSerializer,
    ContractChauffeurSerializer,
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
    GET: list chauffeur contracts (filters: garant, association_user_moto_id, statut, q)
    POST: create chauffeur contract (supports multipart for files)
    """
    queryset = ContratChauffeur.objects.all().order_by("-created")
    serializer_class = ContractChauffeurSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = (JSONParser, MultiPartParser, FormParser)  # ✅ accept JSON + form-data

    def get_queryset(self):
        qs = super().get_queryset()
        garant_id = self.request.query_params.get("garant")
        assoc_id = self.request.query_params.get("association_user_moto_id")
        statut = self.request.query_params.get("statut")
        q = self.request.query_params.get("q")

        if garant_id:
            qs = qs.filter(garant_id=garant_id)
        if assoc_id:
            qs = qs.filter(association_user_moto_id=assoc_id)
        if statut:
            qs = qs.filter(statut=statut)
        if q:
            qs = qs.filter(Q(reference_contrat__icontains=q) | Q(statut__icontains=q))
        return qs


class ContractChauffeurDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: retrieve chauffeur contract
    PUT/PATCH: update (supports multipart for files)
    DELETE: delete
    """
    queryset = ContratChauffeur.objects.all()
    serializer_class = ContractChauffeurSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = (JSONParser, MultiPartParser, FormParser)  # ✅ accept JSON + form-data
