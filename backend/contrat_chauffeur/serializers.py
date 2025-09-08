from datetime import datetime, timedelta
from django.db import transaction, models as dj_models
from .models import ContratBatterie
from rest_framework import serializers
from .models import ContratChauffeur, StatutContrat, FrequencePaiement



STATUS_CHOICES = ("DRAFT", "ACTIVE", "SUSPENDED", "TERMINATED", "COMPLETED")
_ANCHOR = datetime(1970, 1, 1)  # used to encode integer days into your DATETIME column


def _encode_days_as_datetime(days: int) -> datetime:
    return _ANCHOR + timedelta(days=days)


def _compute_days(date_debut, date_fin):
    if date_debut and date_fin:
        delta = (date_fin - date_debut).days
        if delta < 0:
            raise serializers.ValidationError({"date_fin": "date_fin must be on or after date_debut"})
        return delta
    return None


class _DureeJourOutMixin(serializers.ModelSerializer):
    duree_jour_jours = serializers.SerializerMethodField()

    def get_duree_jour_jours(self, obj):
        return _compute_days(obj.date_debut, obj.date_fin)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Hide the internal DATETIME storage; show only the integer days
        data.pop("duree_jour", None)
        return data


class ContratBatterieListSerializer(_DureeJourOutMixin):
    class Meta:
        model = ContratBatterie
        fields = [
            "id", "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "date_signature", "date_enregistrement", "date_debut", "date_fin",
            "duree_jour", "duree_jour_jours",
            "statut", "montant_engage", "montant_caution",
            "chauffeur_id", "created", "updated",
        ]


class ContratBatterieDetailSerializer(ContratBatterieListSerializer):
    pass


class ContratBatterieCreateSerializer(_DureeJourOutMixin):
    class Meta:
        model = ContratBatterie
        fields = [
            "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "date_signature", "date_enregistrement", "date_debut", "duree_jour", "date_fin",
            "statut", "montant_engage", "montant_caution",
            "chauffeur_id",
            # response-only helper:
            "duree_jour_jours",
        ]
        extra_kwargs = {
            "montant_total": {"required": True},
            "date_signature": {"required": True},
            "date_enregistrement": {"required": True},
            "date_debut": {"required": True},
            "montant_engage": {"required": True},
            "montant_caution": {"required": True},
            "chauffeur_id": {"required": True},
            "montant_paye": {"required": False},
            "montant_restant": {"required": False},
            "statut": {"required": False},
            "duree_jour": {"required": False},  # computed
            "date_fin": {"required": False},
        }
        read_only_fields = ("duree_jour",)  # client shouldn't send it

    def validate_statut(self, value):
        if value and value.upper() not in STATUS_CHOICES:
            raise serializers.ValidationError(f"statut must be one of {STATUS_CHOICES}")
        return value

    def validate(self, attrs):
        # amounts
        mt = attrs.get("montant_total")
        mp = attrs.get("montant_paye", 0)
        mr = attrs.get("montant_restant")
        if "montant_paye" not in attrs:
            attrs["montant_paye"] = 0
        if mr is None and mt is not None:
            attrs["montant_restant"] = mt - mp

        # duration
        days = _compute_days(attrs.get("date_debut"), attrs.get("date_fin"))
        if days is not None:
            if isinstance(ContratBatterie._meta.get_field("duree_jour"), dj_models.DateTimeField):
                attrs["duree_jour"] = _encode_days_as_datetime(days)
            else:
                attrs["duree_jour"] = days
        else:
            attrs.pop("duree_jour", None)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        return ContratBatterie.objects.create(**validated_data)


class ContratBatterieUpdateSerializer(_DureeJourOutMixin):
    class Meta:
        model = ContratBatterie
        fields = [
            "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "date_signature", "date_enregistrement", "date_debut", "duree_jour", "date_fin",
            "statut", "montant_engage", "montant_caution",
            "chauffeur_id",
            "duree_jour_jours",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}
        read_only_fields = ("duree_jour",)

    def validate_statut(self, value):
        if value and value.upper() not in STATUS_CHOICES:
            raise serializers.ValidationError(f"statut must be one of {STATUS_CHOICES}")
        return value

    def validate(self, attrs):
        inst = self.instance
        # amounts
        mt = attrs.get("montant_total", inst.montant_total)
        mp = attrs.get("montant_paye", inst.montant_paye)
        if "montant_restant" not in attrs:
            attrs["montant_restant"] = mt - mp

        # duration (use updated or existing dates)
        d_debut = attrs.get("date_debut", inst.date_debut)
        d_fin = attrs.get("date_fin", inst.date_fin)
        days = _compute_days(d_debut, d_fin)
        if days is not None:
            if isinstance(ContratBatterie._meta.get_field("duree_jour"), dj_models.DateTimeField):
                attrs["duree_jour"] = _encode_days_as_datetime(days)
            else:
                attrs["duree_jour"] = days
        return attrs
    
    
    
    
class ContractChauffeurSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContratChauffeur
        read_only_fields = (
            "id",
            "created",
            "updated",
            "montant_restant",
            "jour_conge_restant",
            "reference_contrat",
            "date_enregistrement",  # auto set when activated
        )
        fields = (
            "id",
            "created",
            "updated",
            "reference_contrat",
            "montant_total",
            "montant_paye",
            "montant_restant",
            "frequence_paiement",
            "montant_par_paiement",
            "date_signature",
            "date_enregistrement",
            "date_debut",
            "duree_jour",
            "date_fin",
            "statut",
            "montant_engage",
            "contrat_physique_chauffeur",
            "contrat_physique_batt",
            "contrat_physique_moto_garant",
            "contrat_physique_batt_garant",
            "montant_caution_batt",
            "montant_engage_batt",
            "duree_caution_batt",
            "jour_conge_total",
            "jour_conge_utilise",
            "jour_conge_restant",
            "association_user_moto_id",
            "contrat_batt",
            "garant",
            "regle_penalite",
        )

    def validate(self, attrs):
        # extra business rules at API layer if needed
        mt = attrs.get("montant_total", getattr(self.instance, "montant_total", 0))
        mp = attrs.get("montant_paye", getattr(self.instance, "montant_paye", 0))
        if mt is not None and mp is not None and mp > mt:
            raise serializers.ValidationError("Le montant payé ne peut pas dépasser le montant total.")
        return attrs


class ContractChauffeurStateSerializer(serializers.ModelSerializer):
    """Slim serializer for state transitions (PATCH actions)."""

    class Meta:
        model = ContratChauffeur
        fields = ("id", "statut", "date_enregistrement", "montant_restant")
        read_only_fields = fields
