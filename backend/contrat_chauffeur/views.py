from xml import parsers

from django.db.models import Q
from rest_framework import generics
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import  IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import ContratBatterie, ContratChauffeur, StatutContrat
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
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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
    queryset = ContratChauffeur.objects.all().order_by("-created")
    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return ContractDriverUpdateSerializer if self.request.method in ("PUT", "PATCH") else ContractDriverDetailSerializer


from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
class ModifierStatutContratAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, pk, *args, **kwargs):
        """
        Modifie le statut d’un contrat chauffeur.
        Nécessite les champs :
          - nouveau_statut
          - motif
        """
        nouveau_statut = request.data.get("nouveau_statut")
        motif = (request.data.get("motif") or "").strip()

        # Validation de base
        if not nouveau_statut or nouveau_statut not in StatutContrat.values:
            return Response(
                {"detail": "Statut invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not motif:
            return Response(
                {"detail": "Un motif de modification est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                contrat = ContratChauffeur.objects.select_for_update().get(pk=pk)

                # Si déjà au même statut → inutile
                if contrat.statut == nouveau_statut:
                    return Response(
                        {"detail": f"Le contrat est déjà au statut '{contrat.statut}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # ⚡️ Mise à jour directe — évite tout appel à .save() et donc toute validation
                ContratChauffeur.objects.filter(pk=pk).update(
                    statut=nouveau_statut,
                    date_modification_statut=timezone.now(),
                    motif_modification_statut=motif,
                    statut_modifie_par=request.user,
                    updated=timezone.now()
                )

            return Response(
                {"success": True, "message": f"Statut du contrat modifié en '{nouveau_statut}'."},
                status=status.HTTP_200_OK
            )

        except ContratChauffeur.DoesNotExist:
            return Response(
                {"detail": "Contrat introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ContratChauffeurUpdateAPIView(generics.UpdateAPIView):
    """
    Permet de modifier un contrat chauffeur existant.
    Seuls les champs autorisés peuvent être modifiés.
    Les champs calculés (montant_restant, date_fin, etc.) sont recalculés automatiquement.
    """
    queryset = ContratChauffeur.objects.all()
    serializer_class = ContractDriverUpdateSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        return ContratChauffeur.objects.all()

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
