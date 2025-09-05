from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .serializers import ContractCreateSerializer, ContractActivateSerializer
from .models import ContratChauffeur

class ContractCreateView(generics.CreateAPIView):
    serializer_class = ContractCreateSerializer
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        contract = ser.save()
        return Response({
            "id": contract.id,
            "reference_contrat": contract.reference_contrat,
            "statut": contract.statut,
            "association_user_moto_id": contract.association_user_moto_id,
            "garant_id": contract.garant_id,
            "montant_total": str(contract.montant_total),
            "montant_paye": str(contract.montant_paye),
            "montant_restant": str(contract.montant_restant),
            "frequence_paiement": contract.frequence_paiement,
            "montant_par_paiement": str(contract.montant_par_paiement),
            "date_debut": contract.date_debut,
            "date_fin": contract.date_fin,
        }, status=status.HTTP_201_CREATED)

class ContractActivateView(APIView):
    def post(self, request, pk):
        contract = get_object_or_404(ContratChauffeur, pk=pk)
        ser = ContractActivateSerializer(contract, data=request.data or {}, partial=True)
        ser.is_valid(raise_exception=True)
        contract = ser.save()
        return Response({"id": contract.id, "statut": contract.statut, "updated": contract.updated})
