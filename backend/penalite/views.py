from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import viewsets, mixins
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import  StatutPenalite, TypePenalite
from .models import Penalite, PaiementPenalite
from .serializers import (
    PenaliteListSerializer, PaiementPenaliteCreateSerializer,
)
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
# penalite/views.py
from django.utils import timezone
from datetime import timedelta

# Create your views here.
class PenaliteViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = Penalite.objects.select_related(
        "contrat_chauffeur",
        "contrat_chauffeur__association_user_moto__validated_user",
    ).order_by("-created")
    serializer_class = PenaliteListSerializer

def _auth_user_or_none(request):
    User = get_user_model()
    u = getattr(request, "user", None)
    # AnonymousUser n'est pas une instance de User
    return u if isinstance(u, User) and u.is_authenticated else None

class PaiementPenaliteViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = PaiementPenalite.objects.select_related("penalite", "penalite__contrat_chauffeur")
    serializer_class = PaiementPenaliteCreateSerializer

    def perform_create(self, serializer):
        paiement = serializer.save()
        penalite = paiement.penalite
        contrat = penalite.contrat_chauffeur
        assoc = getattr(contrat, "association_user_moto", None)

        # ✅ Étape 1 : Si la pénalité vient d'être payée, on met à jour son statut
        penalite.statut_penalite = StatutPenalite.PAYE
        penalite.montant_paye = penalite.montant_penalite
        penalite.montant_restant = 0
        penalite.save(update_fields=["statut_penalite", "montant_paye", "montant_restant", "updated"])

        # ✅ Étape 2 : Vérifier s’il reste une autre pénalité non payée ET en retard (> 72h)
        now = timezone.now()
        penalite_en_retard = Penalite.objects.filter(
            contrat_chauffeur=contrat,
            statut_penalite__in=[StatutPenalite.NON_PAYE, StatutPenalite.PARTIELLEMENT_PAYE],
            echeance_paiement_penalite__lt=now
        ).exists()

        # ✅ Étape 3 : Si aucune pénalité en retard → on débloque le swap
        if assoc and not penalite_en_retard:
            assoc.swap_bloque = 1  # 1 = débloqué
            assoc.save(update_fields=["swap_bloque"])

        # ✅ Étape 4 : Sinon, on garde le blocage
        elif assoc:
            assoc.swap_bloque = 0  # toujours bloqué
            assoc.save(update_fields=["swap_bloque"])


class AnnulerPenaliteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request, pk, *args, **kwargs):
        justificatif = (request.data.get("justificatif") or "").strip()
        if not justificatif:
            return Response({"detail": "Un justificatif d'annulation est obligatoire."}, status=400)

        try:
            with transaction.atomic():  # ✅ requis pour select_for_update
                pen = (Penalite.objects
                       .select_for_update()         # ✅ OK sur MySQL/InnoDB
                       .select_related("contrat_chauffeur")
                       .get(pk=pk))

                # Règles métier

                if pen.statut_penalite == StatutPenalite.PAYE:
                    return Response({"detail": "Impossible d'annuler une pénalité déjà payée."}, status=400)
                if pen.statut_penalite == StatutPenalite.PARTIELLEMENT_PAYE:
                    return Response({"detail": "Impossible d'annuler une pénalité partiellement payée."}, status=400)
                if pen.statut_penalite != StatutPenalite.NON_PAYE:
                    return Response({"detail": "Seules les pénalités non payées peuvent être annulées."}, status=400)

                # Mise à jour
                pen.statut_penalite = StatutPenalite.ANNULEE
                pen.justificatif_annulation = justificatif
                pen.annulee_par = request.user
                pen.date_annulation = timezone.now()
                pen.montant_restant = 0
                pen.echeance_paiement_penalite = None
                pen.save(update_fields=[
                    "statut_penalite","justificatif_annulation","annulee_par",
                    "date_annulation","montant_restant","echeance_paiement_penalite","updated"
                ])

            return Response({"success": True, "message": "Pénalité annulée."}, status=200)

        except Penalite.DoesNotExist:
            return Response({"detail": "Pénalité introuvable."}, status=404)