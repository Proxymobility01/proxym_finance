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
from contrat_chauffeur.models import ContratChauffeur
from paiement_lease.models import PaiementLease


# =====================
# Pagination (10/page)
# =====================
class LeasePaymentPagination(PageNumberPagination):
    page_size = 4                     # 👈 10 paiements par page
    page_size_query_param = "page_size"
    max_page_size = 100

def midnight_aware(d):
    """Retourne un datetime à 00:00 pour une date donnée, aware si USE_TZ=True."""
    dt = datetime.combine(d, time.min)
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
    """
    POST /api/lease/pay
    Enregistrement d’un paiement de lease (comportement calqué sur Laravel: J+1, saut dimanche, gestion du gap).
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        # Le serializer accepte: contrat_id, montant_moto, montant_batt, montant_total,
        # methode_paiement, reference_transaction (optionnel), date_paiement_concerne, date_limite_paiement
        serializer = LeasePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Règle "after_or_equal": limite >= concernée (comme la validation Laravel)
        base_concernee = data["date_paiement_concerne"]   # type: date
        base_limite = data["date_limite_paiement"]        # type: date
        if base_limite < base_concernee:
            return Response(
                {"success": False, "message": "La date limite doit être ≥ à la date concernée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                contrat = ContratChauffeur.objects.get(pk=data["contrat_id"])

                # Montants strictement en Decimal
                m_moto = Decimal(data.get("montant_moto") or 0)
                m_batt = Decimal(data.get("montant_batt") or 0)
                m_total = Decimal(data.get("montant_total") or (m_moto + m_batt))
                if (m_moto + m_batt) != m_total:
                    m_total = m_moto + m_batt

                now = timezone.now()
                reference = f"PL-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5].upper()}"
                statut_global = "PAYE" if m_total > 0 else "IMPAYE"

                # Enregistrement du paiement (dates stockées en DateTime à minuit)
                PaiementLease.objects.create(
                    reference_paiement=reference,
                    montant_moto=m_moto,
                    montant_batt=m_batt,
                    montant_total=m_total,
                    date_paiement=now.date(),
                    methode_paiement=data["methode_paiement"],
                    reference_transaction=data.get("reference_transaction", None),  # optionnel
                    type_contrat="CHAUFFEUR",
                    statut=statut_global,
                    contrat_chauffeur=contrat,
                    date_concernee=midnight_aware(base_concernee),
                    date_limite=midnight_aware(base_limite),
                    employe=None,
                    user_agence=None,
                )

                # Avancement du contrat
                contrat.montant_paye = (contrat.montant_paye or Decimal("0")) + m_total
                contrat.montant_restant = max(Decimal("0"), (contrat.montant_total or Decimal("0")) - contrat.montant_paye)

              # Calcul des prochaines échéances (logique Laravel)
                had_gap = base_limite > base_concernee
                next_concernee = next_working_day(base_concernee)
                if had_gap:
                    next_limite = next_working_day(next_concernee)
                else:
                    next_limite = next_concernee

                # Stocker sur le contrat (DateField directement)
                contrat.date_concernee = next_concernee
                contrat.date_limite = next_limite
                contrat.save()

            return Response(
                {"success": True, "message": "Paiement enregistré avec succès."},
                status=status.HTTP_201_CREATED,
            )

        except ContratChauffeur.DoesNotExist:
            return Response(
                {"success": False, "message": "Contrat introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


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
