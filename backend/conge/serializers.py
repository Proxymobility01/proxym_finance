from datetime import timedelta, datetime, time
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework import serializers

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


class CongeBaseSerializer(serializers.ModelSerializer):
    contrat_id_read = serializers.IntegerField(source="contrat.id", read_only=True)
    reference_contrat = serializers.CharField(source="contrat.reference_contrat", read_only=True)
    chauffeur = serializers.SerializerMethodField()

    class Meta:
        model = Conge
        fields = [
            "id",
            "contrat_id_read",     # lecture
            "reference_contrat",   # lecture
            "chauffeur",           # lecture
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
    # contrat_id optionnel → pas besoin de required=True
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

        # Cas 1 : approbation → consomme des jours
        if old_statut != StatutConge.APPROUVE and new_statut == StatutConge.APPROUVE:
            if nb_jour > contrat.jour_conge_restant:
                raise serializers.ValidationError(
                    {"nb_jour": "Pas assez de jours de congés restants."}
                )
            contrat.jour_conge_utilise += nb_jour
            contrat.jour_conge_restant = max(
                contrat.jour_conge_total - contrat.jour_conge_utilise, 0
            )
            contrat.save(update_fields=["jour_conge_utilise", "jour_conge_restant"])

        # Cas 2 : annulation ou rejet d’un congé déjà approuvé → restitution
        elif old_statut == StatutConge.APPROUVE and new_statut in [StatutConge.ANNULE, StatutConge.REJETE]:
            contrat.jour_conge_utilise = max(contrat.jour_conge_utilise - nb_jour, 0)
            contrat.jour_conge_restant = max(
                contrat.jour_conge_total - contrat.jour_conge_utilise, 0
            )
            contrat.save(update_fields=["jour_conge_utilise", "jour_conge_restant"])

        # Cas 3 : passage à "termine" → pas d’effet sur les jours

        return instance
