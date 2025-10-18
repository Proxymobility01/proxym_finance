import csv
import uuid
from io import BytesIO


from django.db.models.aggregates import Sum
from django.db.models.expressions import F, Exists, OuterRef
from django.db.models.fields import DecimalField
from django.db.models.functions.comparison import Coalesce
from decimal import Decimal, ROUND_HALF_UP
from datetime import  timedelta
from django.conf import settings
from django.db import transaction
from django.db.models.functions.datetime import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Value as V
from openpyxl import Workbook
from docxtpl import DocxTemplate
from conge.models import Conge, StatutConge
from penalite.models import Penalite, StatutPenalite
from shared.models import StandardResultsSetPagination
from .filters import PaiementLeaseFilter, NonPaiementLeaseFilter
from .serializers import  LeasePaymentLiteSerializer, \
    LeaseNonPayeLiteSerializer
from contrat_chauffeur.models import ContratChauffeur, StatutContrat
from paiement_lease.models import PaiementLease
from datetime import datetime, date, time, timezone as py_timezone
from django.utils.dateparse import parse_datetime, parse_date
from rest_framework_simplejwt.authentication import JWTAuthentication

# --- Calendrier Paiements ---
from datetime import date, timedelta
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response





def _to_aware_utc(value):
    """
    Convertit 'value' (str|date|datetime|None) en datetime aware en UTC.
    - ISO avec 'Z' ou offset → parse aware puis converti en UTC
    - 'YYYY-MM-DD' → minuit local → rendu aware → converti en UTC
    - naive → rendu aware (timezone courant) → converti en UTC
    - None/parse ratée → 1970-01-01 UTC
    """
    if value is None:
        return datetime(1970, 1, 1, tzinfo=py_timezone.utc)

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time.min)
    elif isinstance(value, str):
        s = value.replace("Z", "+00:00").strip()
        dt = parse_datetime(s)
        if dt is None:
            d = parse_date(s)
            if d is not None:
                dt = datetime.combine(d, time.min)
            else:
                return datetime(1970, 1, 1, tzinfo=py_timezone.utc)
    else:
        return datetime(1970, 1, 1, tzinfo=py_timezone.utc)

    # rendre aware si besoin, en timezone locale Django
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    # convertir en UTC
    return dt.astimezone(py_timezone.utc)



def noon_aware(d):
    """Retourne un datetime à 12:00 (midi) pour une date donnée, aware si USE_TZ=True."""
    dt = datetime.combine(d, time(hour=12))
    if getattr(settings, "USE_TZ", False) and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

def next_working_day(d):
    """Retourne le jour suivant, en sautant le dimanche."""
    nxt = d + timedelta(days=1)
    while nxt.weekday() == 6:  # 6 = dimanche
        nxt += timedelta(days=1)
    return nxt

def add_days_skip_sunday(d, n=1):
    """Ajoute n jours à une date, en sautant les dimanches."""
    result = d
    for _ in range(n):
        result += timedelta(days=1)
        while result.weekday() == 6:
            result += timedelta(days=1)
    return result


class PaiementLeaseAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = LeasePaymentLiteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                contrat = ContratChauffeur.objects.select_for_update().get(pk=data["contrat_id"])

                base_concernee = data.get("date_paiement_concerne") or contrat.date_concernee
                base_limite = data.get("date_limite_paiement") or contrat.date_limite

                today = timezone.localdate()
                today_start = timezone.make_aware(datetime.combine(today, time.min))
                today_end = timezone.make_aware(datetime.combine(today, time.max))

                count_today = (
                    PaiementLease.objects
                    .select_for_update()
                    .filter(
                        contrat_chauffeur=contrat,
                        created__range=(today_start, today_end)
                    )
                    .count()
                )

                if count_today >= 2:
                    return Response(
                        {"success": False, "message": "Limite de 2 paiements par jour atteinte pour ce contrat."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Montants
                m_moto = Decimal(data.get("montant_moto") or 0)
                m_batt = Decimal(data.get("montant_batt") or 0)
                m_total = m_moto + m_batt

                now = timezone.now()
                reference = f"PL-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5].upper()}"
                statut_global = "PAYE" if m_total > 0 else "IMPAYE"

                PaiementLease.objects.create(
                    reference_paiement=reference,
                    montant_moto=m_moto,
                    montant_batt=m_batt,
                    montant_total=m_total,
                    methode_paiement=data["methode_paiement"],
                    reference_transaction=data.get("reference_transaction"),
                    type_contrat="CHAUFFEUR",
                    statut=statut_global,
                    contrat_chauffeur=contrat,
                    date_concernee=base_concernee,
                    date_limite=base_limite,
                    employe=request.user,
                    user_agence=None,
                )

                # ✅ Mise à jour du contrat chauffeur
                contrat.montant_paye = (contrat.montant_paye or Decimal("0")) + m_total
                contrat.montant_restant = max(
                    Decimal("0"),
                    (contrat.montant_total or Decimal("0")) - contrat.montant_paye
                )

                next_concernee = next_working_day(base_concernee)
                next_limite = add_days_skip_sunday(next_concernee, 1)

                contrat.date_concernee = next_concernee
                contrat.date_limite = next_limite
                contrat.save()

                if contrat.contrat_batt:
                    batt = contrat.contrat_batt
                    batt.montant_paye = (batt.montant_paye or Decimal("0")) + m_batt
                    batt.montant_restant = max(
                        Decimal("0"),
                        (batt.montant_total or Decimal("0")) - batt.montant_paye
                    )
                    batt.save(update_fields=["montant_paye", "montant_restant", "updated"])

                # 🟩 --- Nouvelle logique : débloquer le swap si plus de pénalité échue ---
                from penalite.models import Penalite, StatutPenalite
                now = timezone.now()
                penalite_en_retard = Penalite.objects.filter(
                    contrat_chauffeur=contrat,
                    statut_penalite__in=[StatutPenalite.NON_PAYE, StatutPenalite.PARTIELLEMENT_PAYE],
                    echeance_paiement_penalite__lt=now
                ).exists()

                assoc = getattr(contrat, "association_user_moto", None)

                if assoc:
                    if not penalite_en_retard:
                        assoc.swap_bloque = 1  # ✅ Débloqué
                        msg = f"✅ Swap débloqué automatiquement pour chauffeur {assoc.validated_user_id}"
                    else:
                        assoc.swap_bloque = 0  # 🚫 Toujours bloqué
                        msg = f"⛔ Swap maintenu bloqué (pénalité échue) pour chauffeur {assoc.validated_user_id}"

                    assoc.save(update_fields=["swap_bloque"])
                    print(msg)
                # 🟩 --- Fin ajout ---

            return Response({"success": True, "message": "Paiement enregistré avec succès."},
                            status=status.HTTP_201_CREATED)

        except ContratChauffeur.DoesNotExist:
            return Response({"success": False, "message": "Contrat introuvable."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "message": str(e)},

                            status=status.HTTP_400_BAD_REQUEST)


def _sort_key(item: dict) -> datetime:
    return _to_aware_utc(item.get("created") or item.get("date_concernee"))




class LeaseCombinedListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    # --- util arrondi 2 décimales ---
    def _q2(self, val) -> Decimal:
        try:
            d = Decimal(val or 0)
        except Exception:
            d = Decimal(0)
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _parse_iso_date(self, s: str | None) -> date | None:
        s = (s or "").strip()
        if not s:
            return None
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return None

    def _aggregate_paid(self, qs_paid):
        """
        Agrégat PAYE:
          amount = SUM(montant_moto + montant_batt)
          count  = nb de lignes
        """
        agg = qs_paid.aggregate(
            total=Coalesce(
                Sum(
                    Coalesce(F("montant_moto"), V(0, output_field=DecimalField())) +
                    Coalesce(F("montant_batt"), V(0, output_field=DecimalField()))
                ),
                V(0, output_field=DecimalField(max_digits=18, decimal_places=2)),
            )
        )
        total = self._q2(agg["total"] or 0)
        count = qs_paid.count()
        return float(total), count

    def _aggregate_non_paid(self, qs_np):
        """
        Agrégat NON_PAYE:
          amount = somme des montants dus négatifs
                   (-contrat.montant_par_paiement) + (-contrat_batt.montant_par_paiement)
          count  = nb de lignes
        Calcul en Python (dépend de champs liés + signe).
        """
        qs_np = qs_np.select_related("contrat_chauffeur", "contrat_chauffeur__contrat_batt")

        total = Decimal("0.00")
        count = 0
        for pen in qs_np:
            count += 1
            contrat = pen.contrat_chauffeur
            batt = getattr(contrat, "contrat_batt", None)
            moto_due = -self._q2(getattr(contrat, "montant_par_paiement", 0))
            batt_due = -self._q2(getattr(batt, "montant_par_paiement", 0) if batt else 0)
            total += (moto_due + batt_due)

        return float(self._q2(total)), count

    def get(self, request, *args, **kwargs):

        q = (request.GET.get("q") or "").strip()
        statut = (request.GET.get("statut") or "").upper().strip()
        paye_par = (request.GET.get("paye_par") or "").strip()
        agence = (request.GET.get("station") or "").strip()

        dc_eq = self._parse_iso_date(request.GET.get("date_concernee"))
        dc_after = self._parse_iso_date(request.GET.get("date_concernee_after"))
        dc_before = self._parse_iso_date(request.GET.get("date_concernee_before"))

        cr_eq = self._parse_iso_date(request.GET.get("created"))
        cr_after = self._parse_iso_date(request.GET.get("created_after"))
        cr_before = self._parse_iso_date(request.GET.get("created_before"))

        # -------- PAYÉS --------
        paid_qs = (PaiementLease.objects
                   .select_related(
                       "contrat_chauffeur",
                       "contrat_chauffeur__association_user_moto",
                       "contrat_chauffeur__association_user_moto__validated_user",
                       "contrat_chauffeur__association_user_moto__moto_valide",
                       "user_agence",
                       "employe",
                   ))
        paid_qs = PaiementLeaseFilter(request.GET, queryset=paid_qs).qs

        if q:
            paid_qs = paid_qs.filter(
                Q(contrat_chauffeur__association_user_moto__validated_user__user_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__nom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__prenom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__moto_valide__moto_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__moto_valide__vin__icontains=q)
            )
        if paye_par := (request.GET.get("paye_par") or "").strip():
            terms = [t.strip() for t in paye_par.split() if t.strip()]
            q_paye_par = Q()
            for term in terms:
                q_paye_par |= (
                        Q(employe__nom__icontains=term) |
                        Q(employe__prenom__icontains=term) |
                        Q(user_agence__nom__icontains=term) |
                        Q(user_agence__prenom__icontains=term)
                )

            paid_qs = paid_qs.filter(q_paye_par)
        if agence := (request.GET.get("agence") or "").strip():
            terms = [t.strip() for t in agence.split() if t.strip()]
            q_agence = Q()
            for term in terms:
                q_agence |= Q(agences__nom_agence__icontains=term)
            paid_qs = paid_qs.filter(q_agence)
        # -------- NON PAYÉS --------
        np_qs_base = (Penalite.objects
                 .select_related(
                     "contrat_chauffeur",
                     "contrat_chauffeur__association_user_moto",
                     "contrat_chauffeur__association_user_moto__validated_user",
                     "contrat_chauffeur__association_user_moto__moto_valide",
                     "contrat_chauffeur__contrat_batt",
                 )
                 .filter(
                    statut_penalite__in=[StatutPenalite.NON_PAYE,StatutPenalite.PAYE,StatutPenalite.PARTIELLEMENT_PAYE],
                 ))

        # optionnel : appliquer tes filtres “NonPaiementLeaseFilter” avant l’anti-join
        np_qs_base = NonPaiementLeaseFilter(request.GET, queryset=np_qs_base).qs

        # ✅ Anti-join : exclure les pénalités pour lesquelles un paiement de LEASE existe
        np_qs = np_qs_base.annotate(
            lease_paid=Exists(
                PaiementLease.objects.filter(
                    contrat_chauffeur=OuterRef("contrat_chauffeur_id"),
                    date_concernee=OuterRef("date_paiement_manquee"),
                )
            )
        ).filter(lease_paid=False)

        # NB: NonPaiementLeaseFilter ne définit PAS 'created' → il ne s’applique pas ici
        np_qs = NonPaiementLeaseFilter(request.GET, queryset=np_qs).qs

        if q:
            np_qs = np_qs.filter(
                Q(contrat_chauffeur__association_user_moto__validated_user__user_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__nom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__prenom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__moto_valide__moto_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__moto_valide__vin__icontains=q)
            )

        # -------- AGRÉGATS (HORS PAGINATION) --------
        total_paid, count_paid = self._aggregate_paid(paid_qs)
        total_np, count_np = self._aggregate_non_paid(np_qs)
        # =======================
        #        CONGÉS
        # =======================
        def _day_bounds(d):
            """Retourne (start_dt, end_dt) aware pour la date locale d."""
            tz = timezone.get_current_timezone()
            start = timezone.make_aware(datetime.combine(d, time.min), tz)
            end = timezone.make_aware(datetime.combine(d, time.max), tz)
            return start, end

        conge_qs = (
            Conge.objects
            .select_related(
                "contrat",
                "contrat__association_user_moto",
                "contrat__association_user_moto__validated_user",
                "contrat__association_user_moto__moto_valide",
            ).exclude(statut=StatutConge.ANNULE)
        )

        # recherche (q)
        if q:
            conge_qs = conge_qs.filter(
                Q(contrat__association_user_moto__validated_user__user_unique_id__icontains=q) |
                Q(contrat__association_user_moto__validated_user__nom__icontains=q) |
                Q(contrat__association_user_moto__validated_user__prenom__icontains=q) |
                Q(contrat__association_user_moto__moto_valide__moto_unique_id__icontains=q) |
                Q(contrat__association_user_moto__moto_valide__vin__icontains=q)
            )

        # ---- filtre "date concernée" (chevauchement) ----
        # règle DateField : un congé compte si [date_debut..date_fin] chevauche la fenêtre
        if dc_eq:
            conge_qs = conge_qs.filter(date_debut__lte=dc_eq, date_fin__gte=dc_eq)
        else:
            if dc_after and dc_before:
                conge_qs = conge_qs.filter(date_fin__gte=dc_after, date_debut__lte=dc_before)
            elif dc_after:
                conge_qs = conge_qs.filter(date_fin__gte=dc_after)
            elif dc_before:
                conge_qs = conge_qs.filter(date_debut__lte=dc_before)

        # ⚠️ on ne filtre PAS par created pour les congés
        conge_count = conge_qs.count()

        # =======================
        #      PÉNALITÉS
        # =======================
        pen_count_qs = (Penalite.objects
                        .select_related(
            "contrat_chauffeur",
            "contrat_chauffeur__association_user_moto",
            "contrat_chauffeur__association_user_moto__validated_user",
            "contrat_chauffeur__association_user_moto__moto_valide",
        )
                        .exclude(statut_penalite=StatutPenalite.ANNULEE)  # on ignore les annulées
                        )

        # recherche (q)
        if q:
            pen_count_qs = pen_count_qs.filter(
                Q(contrat_chauffeur__association_user_moto__validated_user__user_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__nom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__prenom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__moto_valide__moto_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__moto_valide__vin__icontains=q)
            )

        # filtre "date concernée" = date du paiement manqué
        if dc_eq:
            pen_count_qs = pen_count_qs.filter(date_paiement_manquee=dc_eq)
        else:
            if dc_after and dc_before:
                pen_count_qs = pen_count_qs.filter(date_paiement_manquee__range=(dc_after, dc_before))
            elif dc_after:
                pen_count_qs = pen_count_qs.filter(date_paiement_manquee__gte=dc_after)
            elif dc_before:
                pen_count_qs = pen_count_qs.filter(date_paiement_manquee__lte=dc_before)

        # ⚠️ NE PAS filtrer par created ici
        penalite_count = pen_count_qs.count()

        # -------- META --------
        meta = {
            "totals": {
                "paid": {"amount": total_paid, "count": count_paid},
                "non_paid": {"amount": total_np, "count": count_np},
                "conges": {"count": int(conge_count)},
                "penalites": {"count": int(penalite_count)},
            }
        }

        # -------- Sérialisation des listes --------
        paid_data = LeasePaymentLiteSerializer(paid_qs, many=True).data
        np_data = LeaseNonPayeLiteSerializer(np_qs, many=True).data

        # -------- Filtre global 'statut' (sur les lignes) --------
        if statut == "PAYE":
            all_rows = list(paid_data)
        elif statut == "NON_PAYE":
            all_rows = list(np_data)
        else:
            all_rows = list(paid_data) + list(np_data)

        # -------- Tri commun --------
        def ts(item):
            return _to_aware_utc(item.get("created") or item.get("date_concernee"))

        all_rows.sort(key=ts, reverse=True)

        # -------- Pagination --------
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(all_rows, request, view=self)

        response = paginator.get_paginated_response(page)
        response.data["meta"] = meta
        return response




def build_combined_queryset(request):
    """
    Applique les mêmes filtres que la vue combinée, fusionne PAYE + NON_PAYE,
    trie (created desc), et calcule des agrégats globaux.
    Retourne (rows, aggregates) — sans pagination.
    """
    q       = (request.GET.get("q") or "").strip()
    statut  = (request.GET.get("statut") or "").upper().strip()  # "PAYE" | "NON_PAYE" | ''
    paye_par = (request.GET.get("paye_par") or "").strip()
    agence  = (request.GET.get("agence") or "").strip()

    # ---------- PAYÉS ----------
    paid_qs = (PaiementLease.objects
               .select_related(
                   "contrat_chauffeur",
                   "contrat_chauffeur__association_user_moto",
                   "contrat_chauffeur__association_user_moto__validated_user",
                   "contrat_chauffeur__association_user_moto__moto_valide",
                   "user_agence",
                   "employe",
               ))
    paid_qs = PaiementLeaseFilter(request.GET, queryset=paid_qs).qs

    if q:
        paid_qs = paid_qs.filter(
            Q(contrat_chauffeur__association_user_moto__validated_user__user_unique_id__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__validated_user__nom__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__validated_user__prenom__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__moto_valide__moto_unique_id__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__moto_valide__vin__icontains=q)
        )
    if paye_par := (request.GET.get("paye_par") or "").strip():
        terms = [t.strip() for t in paye_par.split() if t.strip()]
        q_paye_par = Q()
        for term in terms:
            q_paye_par |= (
                    Q(employe__nom__icontains=term) |
                    Q(employe__prenom__icontains=term) |
                    Q(user_agence__nom__icontains=term) |
                    Q(user_agence__prenom__icontains=term)
            )

        paid_qs = paid_qs.filter(q_paye_par)
    if agence := (request.GET.get("agence") or "").strip():
        # 👉 si l'UI envoie "direction" (ou "dir"), on filtre sur agences IS NULL
        if agence.lower() in {"direction", "dir"}:
            paid_qs = paid_qs.filter(agences__isnull=True)
        else:
            # filtre texte normal sur le nom d'agence
            terms = [t.strip() for t in agence.split() if t.strip()]
            q_agence = Q()
            for term in terms:
                q_agence |= Q(agences__nom_agence__icontains=term)
            paid_qs = paid_qs.filter(q_agence)

    paid_ser = LeasePaymentLiteSerializer(paid_qs, many=True)
    paid_rows = [dict(x) for x in paid_ser.data]

    # ---------- NON PAYÉS ----------
    np_qs_base = (Penalite.objects
             .select_related(
                 "contrat_chauffeur",
                 "contrat_chauffeur__association_user_moto",
                 "contrat_chauffeur__association_user_moto__validated_user",
                 "contrat_chauffeur__association_user_moto__moto_valide",
                 "contrat_chauffeur__contrat_batt",
             )
             .filter(
                statut_penalite__in=[StatutPenalite.NON_PAYE, StatutPenalite.PAYE, StatutPenalite.PARTIELLEMENT_PAYE],
             ))
    np_qs_base = NonPaiementLeaseFilter(request.GET, queryset=np_qs_base).qs
    # ✅ Anti-join : exclure les pénalités pour lesquelles un paiement de LEASE existe
    np_qs = np_qs_base.annotate(
        lease_paid=Exists(
            PaiementLease.objects.filter(
                contrat_chauffeur=OuterRef("contrat_chauffeur_id"),
                date_concernee=OuterRef("date_paiement_manquee"),
            )
        )
    ).filter(lease_paid=False)

    if q:
        np_qs = np_qs.filter(
            Q(contrat_chauffeur__association_user_moto__validated_user__user_unique_id__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__validated_user__nom__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__validated_user__prenom__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__moto_valide__moto_unique_id__icontains=q) |
            Q(contrat_chauffeur__association_user_moto__moto_valide__vin__icontains=q)
        )

    np_ser = LeaseNonPayeLiteSerializer(np_qs, many=True)
    np_rows = [dict(x) for x in np_ser.data]

    # ---------- Fusion par "statut" demandé ----------
    if statut == "PAYE":
        all_rows = paid_rows
    elif statut == "NON_PAYE":
        all_rows = np_rows
    else:
        all_rows = paid_rows + np_rows

    # ---------- Tri commun ----------
    all_rows.sort(key=_sort_key, reverse=True)

    # ---------- Agrégats globaux ----------
    from decimal import Decimal
    paid_amount = Decimal("0")
    paid_count  = 0
    np_amount   = Decimal("0")
    np_count    = 0

    for r in all_rows:
        st = (r.get("statut_paiement") or "").upper()
        total = Decimal(str(r.get("montant_total") or 0))
        if st == "PAYE":
            paid_amount += total
            paid_count  += 1
        elif st == "NON_PAYE":
            np_amount += total
            np_count  += 1

    aggregates = {
        "paid": {
            "count": int(paid_count),
            "amount": float(paid_amount),
        },
        "non_paid": {
            "count": int(np_count),
            "amount": float(np_amount),
        }
    }

    return all_rows, aggregates

from django.http.response import HttpResponse
# --- CSV ---
class LeaseCombinedExportCSV(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        # ⬇️ dépaqueter (lignes, agrégats)
        rows, _ = build_combined_queryset(request)  # rows = liste de dict "lite"

        filename = f"leases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        fieldnames = [
            "id","chauffeur","moto_unique_id","moto_vin",
            "montant_moto","montant_batt","montant_total",
            "date_concernee","date_limite","methode_paiement",
            "agences","agences",
            "paye_par","created","source"
        ]
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()

        # sécurisation douce
        for r in (rows or []):
            if not isinstance(r, dict):
                try:
                    r = dict(r)
                except Exception:
                    continue
            writer.writerow({k: r.get(k, "") for k in fieldnames})

        return response



# --- XLSX ---


class LeaseCombinedExportXLSX(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        # ⬇️ dépaqueter
        rows, _ = build_combined_queryset(request)

        filename = f"leases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Leases"

        headers = [
            "Chauffeur","Moto (ID)","VIN",
            "Payé par","Agence","Date concernée","Date paiement" ,
            "Montant moto","Montant batt.","Montant total","Statut"
        ]
        ws.append(headers)

        def getv(d, key, default=""):
            if isinstance(d, dict):
                return d.get(key, default)
            try:
                return dict(d).get(key, default)
            except Exception:
                return default

        for r in (rows or []):
            ws.append([
                getv(r, "chauffeur"),
                getv(r, "moto_unique_id"),
                getv(r, "moto_vin"),
                getv(r, "paye_par"),
                getv(r, "agences"),
                getv(r, "date_concernee"),
                getv(r, "created"),
                getv(r, "montant_moto"),
                getv(r, "montant_batt"),
                getv(r, "montant_total"),
                getv(r, "source"),
            ])

        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(resp)
        return resp


def _fmt_fcfa(n):
    try:
        d = Decimal(str(n or 0))
    except Exception:
        d = Decimal("0")
    s = f"{d:,.2f}".replace(",", " ").replace(".00", "")
    return f"{s} FCFA"

def _fmt_date(d):
    if not d:
        return ""
    # accepte déjà date ou datetime
    from datetime import date, datetime
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    # tolère une chaîne ISO YYYY-MM-DD
    try:
        return datetime.fromisoformat(str(d)).date().strftime("%d/%m/%Y")
    except Exception:
        return str(d)

# --- nouveaux helpers filtres "date concernée" ---
def _parse_iso_date(s: str | None) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _day_bounds(d: date):
    """Bornes timezone-aware [d 00:00:00 .. d 23:59:59.999999] dans le TZ courant."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(d, time.min), tz)
    end   = timezone.make_aware(datetime.combine(d, time.max), tz)
    return start, end


class LeaseCombinedExportDOCX(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        # 1) Même fusion payés/non-payés que la liste (avec ses filtres backend)
        rows, _aggs = build_combined_queryset(request)

        paid_rows, non_paid_rows = [], []
        for r in rows or []:
            row = {
                "chauffeur":      r.get("chauffeur") or "",
                "montant_moto":   _fmt_fcfa(r.get("montant_moto")),
                "montant_batt":   _fmt_fcfa(r.get("montant_batt")),
                "montant_total":  _fmt_fcfa(r.get("montant_total")),
            }
            if (r.get("source") or "").upper() == "PAYE":
                paid_rows.append(row)
            else:
                non_paid_rows.append(row)

        # 2) Filtres communs à conges/penalites : recherche + date_concernee (uniquement)
        q = (request.GET.get("q") or "").strip()
        dc_eq     = _parse_iso_date(request.GET.get("date_concernee"))
        dc_after  = _parse_iso_date(request.GET.get("date_concernee_after"))
        dc_before = _parse_iso_date(request.GET.get("date_concernee_before"))

        # -----------------------
        #        PÉNALITÉS
        # -----------------------
        pens = (Penalite.objects
                .select_related(
                    "contrat_chauffeur",
                    "contrat_chauffeur__association_user_moto",
                    "contrat_chauffeur__association_user_moto__validated_user",
                )
                .exclude(statut_penalite=StatutPenalite.ANNULEE)
                )
        if q:
            pens = pens.filter(
                Q(contrat_chauffeur__association_user_moto__validated_user__user_unique_id__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__nom__icontains=q) |
                Q(contrat_chauffeur__association_user_moto__validated_user__prenom__icontains=q)
            )

        # date_concernee pour pénalités = date_paiement_manquee (DateField)
        if dc_eq:
            pens = pens.filter(date_paiement_manquee=dc_eq)
        else:
            if dc_after and dc_before:
                pens = pens.filter(date_paiement_manquee__range=(dc_after, dc_before))
            elif dc_after:
                pens = pens.filter(date_paiement_manquee__gte=dc_after)
            elif dc_before:
                pens = pens.filter(date_paiement_manquee__lte=dc_before)

        penalites = []
        for p in pens:
            vu = getattr(getattr(p.contrat_chauffeur, "association_user_moto", None), "validated_user", None)
            nom = " ".join(filter(None, [getattr(vu, "nom", ""), getattr(vu, "prenom", "")])).strip() if vu else ""
            penalites.append({
                "chauffeur": nom,
                "montant":   _fmt_fcfa(p.montant_penalite),
                "statut":    p.get_statut_penalite_display() if hasattr(p, "get_statut_penalite_display") else p.statut_penalite,
            })

        # -----------------------
        #          CONGÉS
        # -----------------------
        conges_qs = (
            Conge.objects
            .select_related(
                "contrat",
                "contrat__association_user_moto",
                "contrat__association_user_moto__validated_user",
            )
        )

        if q:
            conges_qs = conges_qs.filter(
                Q(contrat__association_user_moto__validated_user__user_unique_id__icontains=q) |
                Q(contrat__association_user_moto__validated_user__nom__icontains=q) |
                Q(contrat__association_user_moto__validated_user__prenom__icontains=q)
            )

        # Filtre "date concernée" = chevauchement sur [date_debut .. date_fin] (DateField)
        if dc_eq:
            conges_qs = conges_qs.filter(date_debut__lte=dc_eq, date_fin__gte=dc_eq)
        else:
            if dc_after and dc_before:
                conges_qs = conges_qs.filter(date_fin__gte=dc_after, date_debut__lte=dc_before)
            elif dc_after:
                conges_qs = conges_qs.filter(date_fin__gte=dc_after)
            elif dc_before:
                conges_qs = conges_qs.filter(date_debut__lte=dc_before)

        # Construction des lignes
        conges = []
        for c in conges_qs:
            vu = getattr(getattr(c.contrat, "association_user_moto", None), "validated_user", None)
            nom = " ".join(filter(None, [getattr(vu, "nom", ""), getattr(vu, "prenom", "")])).strip() if vu else ""
            # nb_jour si inexistant → calcule (fin - debut + 1)
            nb_jour = getattr(c, "nb_jour", None)
            if nb_jour is None and c.date_debut and c.date_fin:
                nb_jour = (c.date_fin - c.date_debut).days + 1
            conges.append({
                "chauffeur": nom,
                "debut": _fmt_date(c.date_debut),  # accepte maintenant des dates
                "fin": _fmt_date(c.date_fin),
                "reprise": _fmt_date(getattr(c, "date_reprise", None)),  # si tu l’as
                "jours": int(nb_jour or 0),
            })

        # 3) Titre
        if dc_eq:
            report_title = f"RECAPITULATIF DU {dc_eq.strftime('%d/%m/%Y')}"
        elif dc_after and dc_before:
            report_title = f"RECAPITULATIF DU {dc_after.strftime('%d/%m/%Y')} AU {dc_before.strftime('%d/%m/%Y')}"
        elif dc_after:
            report_title = f"RECAPITULATIF À PARTIR DU {dc_after.strftime('%d/%m/%Y')}"
        elif dc_before:
            report_title = f"RECAPITULATIF JUSQU'AU {dc_before.strftime('%d/%m/%Y')}"
        else:
            report_title = f"RECAPITULATIF DU {timezone.localdate().strftime('%d/%m/%Y')}"

        # 4) Rendu du .docx (assure-toi que 'rapport-leases.docx' existe bien)
        tpl_path = settings.BASE_DIR / "templates" / "rapport-leases.docx"
        doc = DocxTemplate(str(tpl_path))
        context = {
            "report_title":  report_title,
            "paid_rows":     paid_rows,
            "non_paid_rows": non_paid_rows,
            "penalites":     penalites,
            "conges":        conges,
        }
        doc.render(context)

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)

        filename = f"leases_{timezone.localtime().strftime('%Y%m%d_%H%M%S')}.docx"
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


class CalendrierPaiementsAPIView(APIView):
    """
    🔹 API calendrier global des paiements (par chauffeur)
    - Liste paginée de tous les chauffeurs avec résumé de leurs paiements et congés.
    - Supporte le filtrage par nom/prénom/id chauffeur via ?search=
    - Résumé inclus pour chaque chauffeur : total_jours, jours_payes, jours_conges.
    """
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # --- Récupération optionnelle du filtre
        search = (request.GET.get("search") or "").strip()

        # --- Préparer la liste de contrats à traiter
        contrats = (
            ContratChauffeur.objects
            .select_related("association_user_moto__validated_user")
            .filter(statut__in=["encours", "termine"])  # seulement actifs ou terminés
        )

        if search:
            contrats = contrats.filter(
                Q(association_user_moto__validated_user__nom__icontains=search)
                | Q(association_user_moto__validated_user__prenom__icontains=search)
                | Q(association_user_moto__validated_user__user_unique_id__icontains=search)
            )

        # --- Pagination DRF standard
        paginator = StandardResultsSetPagination()
        contrats_page = paginator.paginate_queryset(contrats, request, view=self)

        results = []
        today = date.today()

        for contrat in contrats_page:
            chauffeur = getattr(contrat.association_user_moto, "validated_user", None)

            if not contrat.date_debut:
                continue

            date_debut = contrat.date_debut
            date_fin = today  # jusqu'à aujourd'hui

            # 🟢 Récupération des paiements (basé sur created)
            paiements_qs = (
                PaiementLease.objects
                .filter(contrat_chauffeur=contrat)
                .exclude(created__isnull=True)
                .values_list("created", flat=True)
            )

            # Extraction de la date (y compris dimanche)
            jours_payes = sorted({p.date() for p in paiements_qs if p})
            jours_payes_set = set(jours_payes)

            # 🔵 Génération de toutes les dates du contrat
            jours_total = []
            current = date_debut
            while current <= date_fin:
                jours_total.append(current)
                current += timedelta(days=1)

            # 🔴 Congés = jours sans paiement, hors dimanche
            jours_manques = [
                j.strftime("%Y-%m-%d")
                for j in jours_total
                if j not in jours_payes_set and j.weekday() != 6
            ]

            # Conversion ISO
            jours_payes_iso = [j.strftime("%Y-%m-%d") for j in jours_payes]

            # 📊 Résumé
            total_jours = len([j for j in jours_total if j.weekday() != 6])
            total_payes = len(jours_payes_iso)
            total_conges = len(jours_manques)

            # 🧩 Construction du bloc chauffeur
            results.append({
                "contrat": {
                    "id": contrat.id,
                    "nom_chauffeur": getattr(chauffeur, "nom", ""),
                    "prenom_chauffeur": getattr(chauffeur, "prenom", ""),
                    "user_unique_id": getattr(chauffeur, "user_unique_id", ""),
                },
                "paiements": jours_payes_iso,
                "conges": jours_manques,
                "resume": {
                    "total_jours": total_jours,
                    "jours_payes": total_payes,
                    "jours_conges": total_conges,
                }
            })

        # --- Retour paginé
        return paginator.get_paginated_response(results)



