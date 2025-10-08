import csv
import uuid
from django.db.models.aggregates import Sum
from django.db.models.expressions import F
from django.db.models.fields import DecimalField
from django.db.models.functions.comparison import Coalesce
from django.http.response import HttpResponse
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, time 
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Value as V
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

    def _aggregate_paid(self, qs_paid):
        """
        Agrégat PAYE:
          amount = SUM(montant_moto + montant_batt)
          count  = nb de lignes
        """
        agg = qs_paid.aggregate(
            total=Coalesce(
                Sum(F("montant_moto") + F("montant_batt")),
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
        np_qs = (Penalite.objects
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
        meta = {
            "totals": {
                "paid":     {"amount": total_paid, "count": count_paid},
                "non_paid": {"amount": total_np,   "count": count_np},
            }
        }

        # -------- Sérialisation des listes --------
        paid_data = LeasePaymentLiteSerializer(paid_qs, many=True).data
        np_data   = LeaseNonPayeLiteSerializer(np_qs, many=True).data



            # -------- Filtre global 'statut' (appliqué AUX LIGNES, pas aux agrégats) --------
        if statut == "PAYE":
            all_rows = list(paid_data)
        elif statut == "NON_PAYE":
            all_rows = list(np_data)
        else:
            all_rows = list(paid_data) + list(np_data)

        # -------- Tri commun (created desc, fallback date_concernee) --------
        def ts(item):
            return _to_aware_utc(item.get("created") or item.get("date_concernee"))

        all_rows.sort(key=ts, reverse=True)

        # -------- Pagination --------
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(all_rows, request, view=self)

        # injecter meta AU NIVEAU TOP (hors pagination)
        response = paginator.get_paginated_response(page)
        response.data["meta"] = meta
        return response



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
from openpyxl import Workbook

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
            "Effectué par","Agence","Date concernée","Date paiement (création)",
            "Montant moto","Montant batt.","Montant total","Source"
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
                getv(r, "statut_paiement"),
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
