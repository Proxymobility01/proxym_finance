from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import viewsets, mixins
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import  StatutPenalite, TypePenalite
from .models import Penalite, PaiementPenalite
from .serializers import (
    PenaliteListSerializer, PaiementPenaliteCreateSerializer,
)
from django.db import transaction
from django.utils import timezone


# Create your views here.
class PenaliteViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

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


    def post(self, request, pk, *args, **kwargs):
        justificatif = (request.data.get("justificatif") or "").strip()
        if not justificatif:
            return Response(
                {"detail": "Un justificatif d'annulation est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # 🔍 1️⃣ Récupérer la pénalité + contrat + association
                pen = (
                    Penalite.objects
                    .select_for_update()
                    .select_related(
                        "contrat_chauffeur",
                        "contrat_chauffeur__association_user_moto"
                    )
                    .get(pk=pk)
                )

                # 🔒 2️⃣ Vérifications métier
                if pen.statut_penalite == StatutPenalite.PAYE:
                    return Response(
                        {"detail": "Impossible d'annuler une pénalité déjà payée."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if pen.statut_penalite == StatutPenalite.PARTIELLEMENT_PAYE:
                    return Response(
                        {"detail": "Impossible d'annuler une pénalité partiellement payée."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if pen.statut_penalite != StatutPenalite.NON_PAYE:
                    return Response(
                        {"detail": "Seules les pénalités non payées peuvent être annulées."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 🧾 3️⃣ Mise à jour de la pénalité
                pen.statut_penalite = StatutPenalite.ANNULEE
                pen.justificatif_annulation = justificatif
                pen.annulee_par = request.user
                pen.date_annulation = timezone.now()
                pen.montant_restant = 0
                pen.echeance_paiement_penalite = None
                pen.save(update_fields=[
                    "statut_penalite",
                    "justificatif_annulation",
                    "annulee_par",
                    "date_annulation",
                    "montant_restant",
                    "echeance_paiement_penalite",
                    "updated",
                ])

                # 🚀 4️⃣ Débloquer le swap de l'association liée
                contrat = pen.contrat_chauffeur
                if contrat and contrat.association_user_moto:
                    assoc = contrat.association_user_moto
                    assoc.swap_bloque = 1  # ✅ Débloquer
                    assoc.save(update_fields=["swap_bloque"])

            return Response(
                {"success": True, "message": "Pénalité annulée et swap débloqué."},
                status=status.HTTP_200_OK
            )

        except Penalite.DoesNotExist:
            return Response({"detail": "Pénalité introuvable."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)