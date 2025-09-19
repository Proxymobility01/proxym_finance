# conge/serializers.py
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
    EN_COURS   = "en_cours"

    CHOICES = [
        (ANNULE, "Annulé"),
        (EN_ATTENTE, "En attente"),
        (APPROUVE, "Approuvé"),
        (TERMINE, "Terminé"),
        (REJETE, "Rejeté"),
        (EN_COURS, "En cours"),
    ]


def _mk_dt(d):
    """Combine une date (YYYY-MM-DD) en DateTime à minuit, aware si USE_TZ."""
    if isinstance(d, str):
        # 'YYYY-MM-DD' -> date
        y, m, day = map(int, d.split("-"))
        d = datetime(y, m, day).date()
    dt = datetime.combine(d, time.min)
    if getattr(settings, "USE_TZ", False) and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


class CongeSerializer(serializers.ModelSerializer):
    # FRONT envoie contrat_id -> mappe sur FK 'contrat'
    contrat_id = serializers.PrimaryKeyRelatedField(
        source="contrat",
        queryset=ContratChauffeur.objects.all(),
        write_only=True,
        required=True,
    )

    # FRONT envoie nb_jour (singulier) -> mappe sur champ modèle nb_jours (pluriel)
    nb_jour = serializers.IntegerField(source="nb_jours", write_only=True, required=True)

    # Exposition lecture
    nb_jours = serializers.IntegerField(read_only=True)
    reference_contrat = serializers.CharField(source="contrat.reference_contrat", read_only=True)
    chauffeur = serializers.SerializerMethodField()

    # On laisse le backend calculer ces champs
    date_fin = serializers.DateTimeField(read_only=True)
    date_reprise = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Conge
        fields = [
            "id",
            "contrat_id",          # écriture
            "reference_contrat",   # lecture
            "chauffeur",           # lecture
            "date_debut",          # écriture (YYYY-MM-DD ou ISO)
            "date_fin",            # lecture (calculée)
            "date_reprise",        # lecture (calculée)
            "nb_jour",             # écriture (alias -> nb_jours)
            "nb_jours",            # lecture
            "motif_conge",         # si présent dans ton modèle
            "statut",              # lecture
        ]
        read_only_fields = ("date_fin", "date_reprise", "nb_jours", "statut")

    def get_chauffeur(self, obj):
        assoc = getattr(obj.contrat, "association_user_moto", None)
        if assoc and assoc.validated_user:
            return f"{(assoc.validated_user.nom or '').strip()} {(assoc.validated_user.prenom or '').strip()}".strip()
        return None

    def validate(self, attrs):
        """
        On attend ici:
          - attrs['contrat'] (via contrat_id)
          - attrs['date_debut']
          - attrs['nb_jours'] (via nb_jour)
        On calcule date_fin = date_debut + (nb_jours - 1)
                 date_reprise = date_fin + 1
        """
        contrat = attrs.get("contrat")
        date_debut = attrs.get("date_debut")
        nb_jours = attrs.get("nb_jours")

        errors = {}
        if not contrat:
            errors["contrat_id"] = "Ce champ est obligatoire."
        if not date_debut:
            errors["date_debut"] = "Ce champ est obligatoire."
        if not nb_jours:
            errors["nb_jour"] = "Ce champ est obligatoire."
        if errors:
            raise serializers.ValidationError(errors)

        # Normalise date_debut -> datetime
        debut_dt = _mk_dt(date_debut)

        # Calculs
        fin_dt = debut_dt + timedelta(days=int(nb_jours) - 1)
        reprise_dt = fin_dt + timedelta(days=1)

        attrs["date_debut"] = debut_dt
        attrs["date_fin"] = fin_dt
        attrs["date_reprise"] = reprise_dt
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        - Vérifie le nombre de jours restants
        - Définit le statut EN_ATTENTE
        - Crée le congé
        - Met à jour les compteurs du contrat (utilisé/restant)
        """
        contrat: ContratChauffeur = validated_data["contrat"]
        nb_jours = int(validated_data["nb_jours"])

        if nb_jours > contrat.jour_conge_restant:
            raise serializers.ValidationError({"nb_jour": "Pas assez de jours de congés restants."})

        validated_data["statut"] = StatutConge.EN_ATTENTE
        conge = super().create(validated_data)

        # Décrément/ incrément immédiat (si tu préfères le faire à l'approbation, déplace ce code ailleurs)
        contrat.jour_conge_utilise += nb_jours
        contrat.jour_conge_restant = max(contrat.jour_conge_total - contrat.jour_conge_utilise, 0)
        contrat.save(update_fields=["jour_conge_utilise", "jour_conge_restant"])

        return conge
