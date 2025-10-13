from datetime import  datetime, time
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from datetime import timedelta
from contrat_chauffeur.models import ContratChauffeur
from .models import Conge


class StatutConge:
    ANNULE     = "annule"
    EN_ATTENTE = "en_attente"
    APPROUVE   = "approuve"
    TERMINE    = "termine"
    REJETE     = "rejete"

    CHOICES = [
        (ANNULE, "Annulé"),
        (EN_ATTENTE, "En attente"),
        (APPROUVE, "Approuvé"),
        (TERMINE, "Terminé"),
        (REJETE, "Rejeté"),
    ]


def _mk_dt(d):
    """Combine une date (YYYY-MM-DD) en DateTime à minuit, aware si USE_TZ."""
    if isinstance(d, str):
        y, m, day = map(int, d.split("-"))
        d = datetime(y, m, day).date()
    dt = datetime.combine(d, time.min)
    if getattr(settings, "USE_TZ", False) and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


# ✅ Fonctions utilitaires pour ignorer les dimanches
def add_days_skip_sundays(start_date, days_to_add):
    """Ajoute des jours à une date en ignorant les dimanches."""
    current_date = start_date
    added_days = 0

    while added_days < days_to_add:
        current_date += timedelta(days=1)
        # weekday() : 0=lundi ... 6=dimanche
        if current_date.weekday() != 6:
            added_days += 1

    return current_date


def subtract_days_skip_sundays(start_date, days_to_subtract):
    """Soustrait des jours à une date en ignorant les dimanches."""
    current_date = start_date
    removed_days = 0

    while removed_days < days_to_subtract:
        current_date -= timedelta(days=1)
        if current_date.weekday() != 6:
            removed_days += 1

    return current_date



class CongeBaseSerializer(serializers.ModelSerializer):
    contrat_id_read = serializers.IntegerField(source="contrat.id", read_only=True)
    reference_contrat = serializers.CharField(source="contrat.reference_contrat", read_only=True)
    chauffeur = serializers.SerializerMethodField()

    class Meta:
        model = Conge
        fields = [
            "id",
            "contrat_id_read",
            "reference_contrat",
            "chauffeur",
            "date_debut",
            "date_fin",
            "date_reprise",
            "nb_jour",
            "motif_conge",
            "statut",
        ]
        read_only_fields = ("date_fin", "date_reprise", "statut")

    def get_chauffeur(self, obj):
        assoc = getattr(obj.contrat, "association_user_moto", None)
        if assoc and assoc.validated_user:
            return f"{(assoc.validated_user.nom or '').strip()} {(assoc.validated_user.prenom or '').strip()}".strip()
        return None

    def validate(self, attrs):
        # Normalise date_debut
        date_debut = attrs.get("date_debut") or getattr(self.instance, "date_debut", None)
        nb_jour = attrs.get("nb_jour") or getattr(self.instance, "nb_jour", None)

        if date_debut and nb_jour:
            debut_dt = _mk_dt(date_debut)
            fin_dt = debut_dt + timedelta(days=int(nb_jour) - 1)
            reprise_dt = fin_dt + timedelta(days=1)

            attrs["date_debut"] = debut_dt
            attrs["date_fin"] = fin_dt
            attrs["date_reprise"] = reprise_dt
        return attrs


class CongeCreateSerializer(CongeBaseSerializer):
    contrat_id = serializers.PrimaryKeyRelatedField(
        source="contrat",
        queryset=ContratChauffeur.objects.all(),
        write_only=True,
        required=True
    )

    class Meta(CongeBaseSerializer.Meta):
        fields = CongeBaseSerializer.Meta.fields + ["contrat_id"]

    @transaction.atomic
    def create(self, validated_data):
        contrat: ContratChauffeur = validated_data["contrat"]
        nb_jour = int(validated_data["nb_jour"])

        if nb_jour > contrat.jour_conge_restant:
            raise serializers.ValidationError(
                {"nb_jour": "Pas assez de jours de congés restants."}
            )

        validated_data["statut"] = StatutConge.EN_ATTENTE
        return super().create(validated_data)



class CongeUpdateSerializer(CongeBaseSerializer):
    contrat_id = serializers.PrimaryKeyRelatedField(
        source="contrat",
        queryset=ContratChauffeur.objects.all(),
        write_only=True,
        required=False
    )

    class Meta(CongeBaseSerializer.Meta):
        fields = CongeBaseSerializer.Meta.fields + ["contrat_id"]
        read_only_fields = ("date_fin", "date_reprise")

    @transaction.atomic
    def update(self, instance, validated_data):
        old_statut = instance.statut
        new_statut = validated_data.get("statut", instance.statut)

        # 🔒 Règle 1 : impossible d’approuver un congé annulé/rejeté
        if old_statut in [StatutConge.ANNULE, StatutConge.REJETE] and new_statut == StatutConge.APPROUVE:
            raise serializers.ValidationError(
                {"statut": "Impossible d’approuver un congé déjà annulé ou rejeté."}
            )

        # 🔒 Règle 2 : impossible de passer de ANNULÉ → REJETÉ ou REJETÉ → ANNULÉ
        if (old_statut == StatutConge.ANNULE and new_statut == StatutConge.REJETE) or \
           (old_statut == StatutConge.REJETE and new_statut == StatutConge.ANNULE):
            raise serializers.ValidationError(
                {"statut": "Impossible de changer un congé annulé en rejeté ou inversement."}
            )

        instance = super().update(instance, validated_data)

        contrat: ContratChauffeur = instance.contrat
        nb_jour = instance.nb_jour

        # Cas 1 : approbation → consomme des jours + ajuste le calendrier
        if old_statut != StatutConge.APPROUVE and new_statut == StatutConge.APPROUVE:
            if nb_jour > contrat.jour_conge_restant:
                raise serializers.ValidationError(
                    {"nb_jour": "Pas assez de jours de congés restants."}
                )

            contrat.jour_conge_utilise += nb_jour
            contrat.jour_conge_restant = max(
                contrat.jour_conge_total - contrat.jour_conge_utilise, 0
            )

            # -- maj du calendrier de paiement (en sautant les dimanches)
            if contrat.date_concernee:
                contrat.date_concernee = add_days_skip_sundays(contrat.date_concernee, nb_jour)
            if contrat.date_limite:
                contrat.date_limite = add_days_skip_sundays(contrat.date_limite, nb_jour)

            contrat.save(update_fields=[
                "jour_conge_utilise", "jour_conge_restant",
                "date_concernee", "date_limite"
            ])

        # Cas 2 : annulation ou rejet d’un congé déjà approuvé → restitution
        elif old_statut == StatutConge.APPROUVE and new_statut in [StatutConge.ANNULE, StatutConge.REJETE]:
            contrat.jour_conge_utilise = max(contrat.jour_conge_utilise - nb_jour, 0)
            contrat.jour_conge_restant = max(
                contrat.jour_conge_total - contrat.jour_conge_utilise, 0
            )

            # 🕓 rétablir les dates initiales (retirer les jours ajoutés, sans compter les dimanches)
            if contrat.date_concernee:
                contrat.date_concernee = subtract_days_skip_sundays(contrat.date_concernee, nb_jour)
            if contrat.date_limite:
                contrat.date_limite = subtract_days_skip_sundays(contrat.date_limite, nb_jour)

            contrat.save(update_fields=[
                "jour_conge_utilise", "jour_conge_restant",
                "date_concernee", "date_limite"
            ])

        return instance
