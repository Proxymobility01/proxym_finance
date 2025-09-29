import uuid
from datetime import timedelta
from decimal import Decimal
from datetime import datetime, timedelta, time 
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

from .serializers import LeasePaymentSerializer
from contrat_chauffeur.models import ContratChauffeur, StatutContrat
from paiement_lease.models import PaiementLease


class LeasePaymentPagination(PageNumberPagination):
    page_size = 4                     # 👈 10 paiements par page
    page_size_query_param = "page_size"
    max_page_size = 100


def noon_aware(d):
    """Retourne un datetime à 12:00 (midi) pour une date donnée, aware si USE_TZ=True."""
    dt = datetime.combine(d, time(hour=12))
    if getattr(settings, "USE_TZ", False) and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def next_working_day(d):
    """J+1 avec saut du dimanche (comme Laravel)."""
    nxt = d + timedelta(days=1)
    if nxt.weekday() == 6:  # 0=lundi … 6=dimanche
        nxt += timedelta(days=1)
    return nxt


class LeasePaymentAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = LeasePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                contrat = ContratChauffeur.objects.select_for_update().get(pk=data["contrat_id"])

                # ✅ Source de vérité : dates du contrat
                base_concernee = contrat.date_concernee
                base_limite    = contrat.date_limite

                # Montants
                m_moto  = Decimal(data.get("montant_moto") or 0)
                m_batt  = Decimal(data.get("montant_batt") or 0)
                m_total = Decimal(data.get("montant_total") or (m_moto + m_batt))
                if (m_moto + m_batt) != m_total:
                    m_total = m_moto + m_batt

                now = timezone.now()
                reference = f"PL-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5].upper()}"
                statut_global = "PAYE" if m_total > 0 else "IMPAYE"

                # ✅ Enregistrer le paiement
                PaiementLease.objects.create(
                    reference_paiement=reference,
                    montant_moto=m_moto,
                    montant_batt=m_batt,
                    montant_total=m_total,
                    methode_paiement=data["methode_paiement"],
                    reference_transaction=data.get("reference_transaction", None),
                    type_contrat="CHAUFFEUR",
                    statut=statut_global,
                    contrat_chauffeur=contrat,
                    date_concernee=base_concernee,
                    date_limite=base_limite,
                    employe=None,
                    user_agence=None,
                )

                # ✅ Mise à jour du contrat chauffeur
                contrat.montant_paye = (contrat.montant_paye or Decimal("0")) + m_total
                contrat.montant_restant = max(
                    Decimal("0"),
                    (contrat.montant_total or Decimal("0")) - contrat.montant_paye
                )

                next_concernee = next_working_day(base_concernee)
                next_limite = next_concernee + timedelta(days=1)

                contrat.date_concernee = next_concernee
                contrat.date_limite    = next_limite
                contrat.save()

                # ✅ Mise à jour du contrat batterie lié
                if contrat.contrat_batt:
                    batt = contrat.contrat_batt
                    batt.montant_paye = (batt.montant_paye or Decimal("0")) + m_batt
                    batt.montant_restant = max(
                        Decimal("0"),
                        (batt.montant_total or Decimal("0")) - batt.montant_paye
                    )
                    batt.save(update_fields=["montant_paye", "montant_restant", "updated"])

            return Response({"success": True, "message": "Paiement enregistré avec succès."},
                            status=status.HTTP_201_CREATED)

        except ContratChauffeur.DoesNotExist:
            return Response({"success": False, "message": "Contrat introuvable."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "message": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)






# =====================
# Liste paginée (GET)
# =====================
class LeasePaymentListAPIView(generics.ListAPIView):
    """
    GET /api/lease/payments?page=1&page_size=10
    👉 Retourne la liste paginée des paiements
    """
    queryset = PaiementLease.objects.all().order_by("-created")
    serializer_class = LeasePaymentSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = LeasePaymentPagination


# =====================
# Détail (GET par ID)
# =====================
class LeasePaymentDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/lease/payments/<id>
    👉 Récupérer un paiement spécifique par son ID
    """
    queryset = PaiementLease.objects.all()
    serializer_class = LeasePaymentSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class LeaseSuiviAPIView(APIView):
    """
    GET /api/lease/suivi
    👉 Retourne pour chaque contrat chauffeur en cours :
       - la date_concernee + date_limite
       - le paiement du jour si existant, sinon null
       - statut = PAYE ou NON_PAYE
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        results = []

        contrats = ContratChauffeur.objects.filter(statut=StatutContrat.ENCOURS)

        for contrat in contrats:
            jour = contrat.date_concernee or today

            paiement = PaiementLease.objects.filter(
                contrat_chauffeur=contrat,
                date_concernee=jour,
                statut="PAYE"
            ).order_by("created").first()

            results.append({
                "contrat_id": contrat.id,
                "chauffeur": str(contrat.association_user_moto.validated_user) if contrat.association_user_moto and contrat.association_user_moto.validated_user else None,
                "date_concernee": jour,
                "date_limite": contrat.date_limite,
                "statut": "PAYE" if paiement else "NON_PAYE",
                "paiement": {
                    "id": paiement.id,
                    "montant_total": str(paiement.montant_total),
                    "created": paiement.created,
                } if paiement else None
            })

        return Response(results)