

# penalite/services.py

from django.db import transaction
from django.utils import timezone
from datetime import date, datetime, time, timedelta

from conge.models import Conge, StatutConge
from contrat_chauffeur.models import ContratChauffeur, StatutContrat
from paiement_lease.models import PaiementLease
from .models import Penalite, TypePenalite, StatutPenalite

import logging
logger = logging.getLogger(__name__)

PENALITE_LEGERE = 2000
PENALITE_GRAVE  = 5000


def _deadline_noon_from_jour(jour: date):
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(jour + timedelta(days=1), time(hour=4)), tz)


def _limit_14h_from_jour(jour: date):
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(jour + timedelta(days=1), time(hour=14)), tz)

def _is_on_leave(contrat, jour: date) -> bool:
    """
    Retourne True si le contrat chauffeur est en congé approuvé couvrant le jour donné.
    """
    start_of_day = datetime.combine(jour, time.min)
    end_of_day   = datetime.combine(jour, time.max)
    tz = timezone.get_current_timezone()
    start_of_day = timezone.make_aware(start_of_day, tz)
    end_of_day   = timezone.make_aware(end_of_day, tz)

    return Conge.objects.filter(
        contrat=contrat,
        statut=StatutConge.APPROUVE,
        date_debut__lte=end_of_day,
        date_fin__gte=start_of_day,
    ).exists()


def _is_paid_for_day(contrat, jour: date) -> bool:
    """
    Retourne True s'il existe un paiement enregistré pour le jour J,
    créé avant la deadline J+1 à 12h locale.
    """
    deadline = _deadline_noon_from_jour(jour)

    return PaiementLease.objects.filter(
        contrat_chauffeur=contrat,
        date_concernee=jour,
        created__lte=deadline,
        statut="PAYE",
        montant_total__gte=(contrat.montant_par_paiement or 0),
    ).exists()


@transaction.atomic
def apply_penalties_for_now(force_window: str | None = None) -> dict:
    now = timezone.localtime()
    today = now.date()
    hour = now.hour
    window = force_window if force_window in ("noon", "fourteen") else ("noon" if hour < 14 else "fourteen")

    created = escalated = unchanged = paid_skipped = leave_skipped = 0

    if window == "noon":
        # Option B : traiter tous les jours manqués, mais uniquement si l’échéance de J est passée (J+1 12:00 ≤ now)
        contrats = ContratChauffeur.objects.select_for_update().filter(statut=StatutContrat.ENCOURS)

        for contrat in contrats:
            current_day = (contrat.date_concernee or today)

            while current_day <= today:
                deadline = _deadline_noon_from_jour(current_day)
                if now < deadline:
                    break

                if _is_on_leave(contrat, current_day):
                    leave_skipped += 1
                    current_day += timedelta(days=1)
                    continue

                if _is_paid_for_day(contrat, current_day):
                    paid_skipped += 1
                else:

                    date_limite_snapshot = contrat.date_limite or current_day

                    pen, was_created = Penalite.objects.get_or_create(
                        contrat_chauffeur=contrat,
                        date_paiement_manquee=current_day,
                        defaults=dict(
                            type_penalite=TypePenalite.LEGERE,
                            montant_penalite=PENALITE_LEGERE,
                            motif_penalite="Paiement non reçu avant 12h",
                            statut_penalite=StatutPenalite.NON_PAYE,
                            description=f"Pénalité automatique légère du {current_day.isoformat()}",
                            montant_paye=0,
                            montant_restant=PENALITE_LEGERE,
                            echeance_paiement_penalite=now + timedelta(hours=72),
                            date_limite_reference=date_limite_snapshot,
                        ),
                    )
                    if was_created:
                        created += 1
                    else:
                        unchanged += 1

                current_day += timedelta(days=1)

    else:
        # 14h : escalader les LÉGÈRES d’hier
        target_jour = today - timedelta(days=1)
        deadline = _deadline_noon_from_jour(target_jour)
        limit14 = _limit_14h_from_jour(target_jour)

        pens = (Penalite.objects
                .select_related("contrat_chauffeur")
                .select_for_update()
                .filter(date_paiement_manquee=target_jour, type_penalite=TypePenalite.LEGERE))

        for pen in pens:
            contrat = pen.contrat_chauffeur

            if _is_on_leave(contrat, target_jour):
                leave_skipped += 1
                continue

            # 1) payé à temps (<= 12h) → skip
            if _is_paid_for_day(contrat, target_jour):
                paid_skipped += 1
                continue

            # 2) payé en retard mais avant 14h → garder légère
            lease_paid_late = PaiementLease.objects.filter(
                contrat_chauffeur=contrat,
                date_concernee=target_jour,
                created__gt=deadline,
                created__lte=limit14,
                statut="PAYE",
            ).exists()

            if lease_paid_late:
                unchanged += 1
                continue

            # 3) toujours pas payé → escalade
            restant = max((pen.montant_penalite or 0) - (pen.montant_paye or 0), 0)
            if restant <= 0 or pen.statut_penalite == StatutPenalite.PAYE:
                unchanged += 1
                continue

            pen.type_penalite = TypePenalite.GRAVE
            pen.montant_penalite = PENALITE_GRAVE
            pen.motif_penalite = "Paiement de lease non reçu avant 14h"
            pen.montant_restant = max(pen.montant_penalite - (pen.montant_paye or 0), 0)
            prefix = (pen.description + " | ") if pen.description else ""
            pen.description = f"{prefix}Escalade automatique en grave le {now.strftime('%Y-%m-%d %H:%M')}"
            pen.save(update_fields=[
                "type_penalite", "montant_penalite", "motif_penalite",
                "montant_restant", "description",
            ])
            escalated += 1

    res = {
        "window": window,
        "created": created,
        "escalated": escalated,
        "unchanged": unchanged,
        "paid_skipped": paid_skipped,
    }
    logger.info("[PENALITES] %s -> %s", window, res)
    return res
