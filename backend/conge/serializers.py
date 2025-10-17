from datetime import date, timedelta
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


# ✅ Nouveau: produit toujours une date (YYYY-MM-DD -> date)
def _mk_date(d):
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        # tolère "YYYY-MM-DD"
        y, m, day = map(int, d.split("-"))
        return date(y, m, day)
    raise serializers.ValidationError({"date_debut": "Format de date invalide."})


# ✅ Fonctions utilitaires pour ignorer les dimanches (fonctionnent avec des 'date')
def add_days_skip_sundays(start_date: date, days_to_add: int) -> date:
    current_date = start_date
    added_days = 0
    while added_days < days_to_add:
        current_date += timedelta(days=1)
        if current_date.weekday() != 6:  # 6 = dimanche
            added_days += 1
    return current_date

def subtract_days_skip_sundays(start_date: date, days_to_subtract: int) -> date:
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
            "date_debut",    # <-- Model: DateField
            "date_fin",      # <-- Model: DateField
            "date_reprise",  # <-- Model: DateField (si tu l’as), sinon enlève cette ligne
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
        # On calcule fin/reprise à partir d'une DATE (plus de datetime)
        date_debut = attrs.get("date_debut") or getattr(self.instance, "date_debut", None)
        nb_jour = attrs.get("nb_jour") or getattr(self.instance, "nb_jour", None)

        if date_debut and nb_jour:
            debut_d = _mk_date(date_debut)
            try:
                nb = int(nb_jour)
            except Exception:
                raise serializers.ValidationError({"nb_jour": "Valeur invalide."})
            if nb < 1:
                raise serializers.ValidationError({"nb_jour": "Doit être ≥ 1."})

            fin_d = debut_d + timedelta(days=nb - 1)
            reprise_d = fin_d + timedelta(days=1)

            attrs["date_debut"] = debut_d
            attrs["date_fin"] = fin_d
            # si ton modèle a date_reprise:
            attrs["date_reprise"] = reprise_d

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
        nb_jour = int(instance.nb_jour or 0)

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

            # -- rétablir les dates initiales (retirer les jours ajoutés, sans compter les dimanches)
            if contrat.date_concernee:
                contrat.date_concernee = subtract_days_skip_sundays(contrat.date_concernee, nb_jour)
            if contrat.date_limite:
                contrat.date_limite = subtract_days_skip_sundays(contrat.date_limite, nb_jour)

            contrat.save(update_fields=[
                "jour_conge_utilise", "jour_conge_restant",
                "date_concernee", "date_limite"
            ])

        return instance
