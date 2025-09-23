from datetime import datetime, timedelta
from math import ceil

from django.db import transaction, models as dj_models

from app_legacy.models import AssociationUserMoto
from garant.models import Garant
from .models import ContratBatterie
from rest_framework import serializers
from .models import ContratChauffeur, StatutContrat, FrequencePaiement



_ANCHOR = datetime(1970, 1, 1)


def _map_choice(value, *, field_name: str | None = None):
    """Valide que le statut envoyé est bien dans les choices FR définis dans le modèle."""
    if value is None:
        return value
    v = str(value).strip()
    if field_name:
        field = ContratChauffeur._meta.get_field(field_name)
        allowed = {str(code) for code, _ in (field.choices or [])}
        if allowed and v not in allowed:
            raise serializers.ValidationError(
                {field_name: f"Valeur invalide '{value}'. Autorisés: {sorted(allowed)}"}
            )
    return v



def _encode_days_as_datetime(days: int) -> datetime:
    return _ANCHOR + timedelta(days=days)


def _compute_days(date_debut, date_fin):
    if date_debut and date_fin:
        delta = (date_fin - date_debut).days
        if delta < 0:
            raise serializers.ValidationError({"date_fin": "date_fin must be on or after date_debut"})
        return delta
    return None


def _compute_fin_and_duration(*, date_debut, montant_total, montant_paye=0, montant_par_paiement=3500):
    """
    Returns (date_fin, duree_jour_days) based on remaining amount / daily payment.
    """
    remaining = max((montant_total or 0) - (montant_paye or 0), 0)
    days_needed = ceil(remaining / (montant_par_paiement or 3500)) if remaining > 0 else 0
    date_fin = date_debut + timedelta(days=days_needed) if date_debut else None
    return date_fin, days_needed




class _DureeJourOutMixin(serializers.ModelSerializer):
    """Hide internal duree_jour storage and expose the integer days as 'duree_jour_jours'."""
    duree_jour_jours = serializers.SerializerMethodField()

    def get_duree_jour_jours(self, obj):
        return _compute_days(obj.date_debut, obj.date_fin)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("duree_jour", None)
        return data




class ContractBatteryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContratBatterie
        fields = [
            "id", "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "date_signature", "date_debut", "date_fin","proprietaire",
            "duree_jour",
            "statut", "montant_engage",
            "contrat_physique_batt",
            "created", "updated",
        ]


class ContractBatteryDetailSerializer(ContractBatteryListSerializer):
    pass


class ContractBatteryCreateSerializer(serializers.ModelSerializer):
    contrat_physique_batt = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = ContratBatterie
        fields = [
            "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "date_signature", "date_debut", "date_fin",
            "statut", "montant_engage","montant_par_paiement",
            "contrat_physique_batt",
        ]
        read_only_fields = ("duree_jour",)

    def validate_statut(self, value):
        return _map_choice(value, field_name="statut")

    def validate(self, attrs):
        mt = attrs.get("montant_total")
        mp = attrs.get("montant_paye", 0)
        if "montant_paye" not in attrs:
            attrs["montant_paye"] = 0
        if attrs.get("montant_restant") is None and mt is not None:
            attrs["montant_restant"] = mt - mp

        # Compute duration
        days = _compute_days(attrs.get("date_debut"), attrs.get("date_fin"))
        if days is not None:
            field = ContratBatterie._meta.get_field("duree_jour")
            attrs["duree_jour"] = _encode_days_as_datetime(days) if isinstance(field, dj_models.DateTimeField) else days
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        return ContratBatterie.objects.create(**validated_data)


class ContractBatteryUpdateSerializer(serializers.ModelSerializer):
    contrat_physique_batt = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = ContratBatterie
        fields = [
            "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "date_signature", "date_debut", "date_fin",
            "statut", "montant_engage", "montant_caution",
            "contrat_physique_batt",
        ]
        read_only_fields = ("duree_jour",)

    def validate_statut(self, value):
        return _map_choice(value, field_name="statut")

    def validate(self, attrs):
        inst = self.instance
        mt = attrs.get("montant_total", inst.montant_total)
        mp = attrs.get("montant_paye", inst.montant_paye)
        if "montant_restant" not in attrs:
            attrs["montant_restant"] = mt - mp

        # duration
        d_debut = attrs.get("date_debut", inst.date_debut)
        d_fin = attrs.get("date_fin", inst.date_fin)
        days = _compute_days(d_debut, d_fin)
        if days is not None:
            field = ContratBatterie._meta.get_field("duree_jour")
            attrs["duree_jour"] = _encode_days_as_datetime(days) if isinstance(field, dj_models.DateTimeField) else days
        return attrs

    def update(self, instance, validated_data):
        # Handle file replacement
        file = validated_data.get("contrat_physique_batt")
        if file:
            if instance.contrat_physique_batt:
                instance.contrat_physique_batt.delete(save=False)
            instance.contrat_physique_batt = file

        # Update other fields
        for attr, value in validated_data.items():
            if attr != "contrat_physique_batt":
                setattr(instance, attr, value)
        instance.save()
        return instance

    


# ---------- LIST / DETAIL ----------
from datetime import datetime, timedelta
from math import ceil

from django.db import transaction, models as dj_models
from django.utils import timezone
from rest_framework import serializers

from .models import ContratChauffeur

# -------------------------------------------------------------------
# Constants & Helpers
# -------------------------------------------------------------------

_ANCHOR = datetime(1970, 1, 1)



def _map_choice(value, *, field_name: str | None = None):
    """Valide que le statut envoyé est bien dans les choices FR définis dans le modèle."""
    if value is None:
        return value
    v = str(value).strip()
    if field_name:
        field = ContratChauffeur._meta.get_field(field_name)
        allowed = {str(code) for code, _ in (field.choices or [])}
        if allowed and v not in allowed:
            raise serializers.ValidationError(
                {field_name: f"Valeur invalide '{value}'. Autorisés: {sorted(allowed)}"}
            )
    return v



def _encode_days_as_datetime(days: int) -> datetime:
    return _ANCHOR + timedelta(days=days)


def _compute_days(date_debut, date_fin):
    if date_debut and date_fin:
        delta = (date_fin - date_debut).days
        if delta < 0:
            raise serializers.ValidationError({"date_fin": "date_fin must be on or after date_debut"})
        return delta
    return None


def _compute_fin_and_duration(*, date_debut, montant_total, montant_paye=0, montant_par_paiement=3500):
    """
    Returns (date_fin, duree_jour_days) based on remaining amount / daily payment.
    """
    remaining = max((montant_total or 0) - (montant_paye or 0), 0)
    days_needed = ceil(remaining / (montant_par_paiement or 3500)) if remaining > 0 else 0
    date_fin = date_debut + timedelta(days=days_needed) if date_debut else None
    return date_fin, days_needed



class _DureeJourOutMixin(serializers.ModelSerializer):
    """Hide internal duree_jour storage and expose the integer days as 'duree_jour_jours'."""
    duree_jour_jours = serializers.SerializerMethodField()

    def get_duree_jour_jours(self, obj):
        return _compute_days(obj.date_debut, obj.date_fin)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("duree_jour", None)
        return data


# -------------------------------------------------------------------
# LIST / DETAIL
# -------------------------------------------------------------------
class ContractDriverListSerializer(_DureeJourOutMixin):
    garant = serializers.SerializerMethodField()
    chauffeur = serializers.SerializerMethodField()
    reference_contrat_batt = serializers.SerializerMethodField()
    montant_par_paiement_batt = serializers.SerializerMethodField()
    montant_engage_batt = serializers.SerializerMethodField()
    class Meta:
        model = ContratChauffeur

        fields = [
            "id", "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
             "montant_par_paiement",
            "montant_par_paiement_batt",
            "montant_engage_batt",
            "date_signature", "date_debut", "date_fin",
            "duree_jour",
            "statut", "montant_engage",
            "contrat_physique_chauffeur",
            "contrat_physique_moto_garant",
            "contrat_physique_batt_garant",
            "jour_conge_total",
            "jour_conge_utilise",
            "jour_conge_restant",
            "association_user_moto_id",  # expose FK id in list
            "contrat_batt",
            "garant",
            "regle_penalite",
            "date_concernee",
            "date_limite",
            "garant",
            "chauffeur",
            "reference_contrat_batt",
        ]

    def get_garant(self, obj):
        if obj.garant:
            return f"{obj.garant.nom or ''} {obj.garant.prenom or ''}".strip()
        return None

    def get_chauffeur(self, obj):
        assoc = obj.association_user_moto
        if assoc and assoc.validated_user:
            vu = assoc.validated_user
            return f"{vu.nom or ''} {vu.prenom or ''}".strip()
        return None

    def get_reference_contrat_batt(self, obj):
        if obj.contrat_batt:
            return obj.contrat_batt.reference_contrat
        return None

    def get_montant_par_paiement_batt(self, obj):
        """Retourne le montant par paiement de la batterie liée"""
        if obj.contrat_batt:
            return obj.contrat_batt.montant_par_paiement
        return None

    def get_montant_engage_batt(self, obj):
        if obj.contrat_batt:
            return obj.contrat_batt.montant_engage
        return None

class ContractDriverDetailSerializer(ContractDriverListSerializer):
    pass


# -------------------------------------------------------------------
# CREATE
# -------------------------------------------------------------------
class ContractDriverCreateSerializer(serializers.ModelSerializer):
    contrat_physique_chauffeur = serializers.FileField(required=False, allow_null=True)
    contrat_physique_batt = serializers.FileField(required=False, allow_null=True)
    contrat_physique_moto_garant = serializers.FileField(required=False, allow_null=True)
    contrat_physique_batt_garant = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = ContratChauffeur
        # NOTE: date_enregistrement intentionally not present here
        fields = [
            "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
            "montant_par_paiement",
            "date_signature", "date_debut", "date_fin",
            "duree_jour",
            "montant_engage",
            "contrat_physique_chauffeur",
            "contrat_physique_batt",
            "contrat_physique_moto_garant",
            "contrat_physique_batt_garant",
            "jour_conge_total",
            "jour_conge_utilise",
            "jour_conge_restant",
            "association_user_moto",  # ✅ writable FK
            "contrat_batt",
            "garant",
            "regle_penalite",
        ]
        read_only_fields = ("duree_jour", "date_fin", "montant_restant")

    # keep method to stay compatible if 'statut' is ever passed in POST
    def validate_statut(self, value):
        # If your model uses FR codes, map and verify against choices
        return _map_choice(value, field_name="statut")

    def validate(self, attrs):
        today = timezone.now().date()

        # ✅ Always allow/clamp date_signature to avoid model clean() errors
        sig = attrs.get("date_signature")
        if not sig or sig > today:
            attrs["date_signature"] = today

        # defaults
        if attrs.get("montant_paye") is None:
            attrs["montant_paye"] = 0

        # montant_restant
        mt = attrs.get("montant_total")
        mp = attrs.get("montant_paye", 0)
        if attrs.get("montant_restant") is None and mt is not None:
            attrs["montant_restant"] = mt - mp

        # date_debut default = today if not provided
        if not attrs.get("date_debut"):
            attrs["date_debut"] = today

        # montant_par_paiement default = 3500 if not provided
        mpp = attrs.get("montant_par_paiement") or 3500
        attrs["montant_par_paiement"] = mpp

        # auto compute date_fin & duree_jour (days)
        date_fin, days = _compute_fin_and_duration(
            date_debut=attrs["date_debut"],
            montant_total=mt or 0,
            montant_paye=mp or 0,
            montant_par_paiement=mpp,
        )
        attrs["date_fin"] = date_fin

        # internal duree_jour storage support
        field = ContratChauffeur._meta.get_field("duree_jour")
        attrs["duree_jour"] = _encode_days_as_datetime(days) if isinstance(field, dj_models.DateTimeField) else days

        # congés restant
        jtot = attrs.get("jour_conge_total", 0)
        juse = attrs.get("jour_conge_utilise", 0)
        attrs["jour_conge_restant"] = (jtot or 0) - (juse or 0)

        # safety
        if mt is not None and mp is not None and mp > mt:
            raise serializers.ValidationError("Le montant payé ne peut pas dépasser le montant total.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        contrat = ContratChauffeur.objects.create(**validated_data)

        # --- Attribuer le proprietaire de la batterie si vide
        batt: ContratBatterie | None = contrat.contrat_batt
        if batt and not (batt.proprietaire and batt.proprietaire.strip()):
            # 1) priorité: le titulaire (validated_user) de l'association
            owner = ""
            assoc: AssociationUserMoto | None = contrat.association_user_moto
            if assoc and assoc.validated_user:
                vu = assoc.validated_user
                owner = " ".join(filter(None, [(vu.nom or "").strip(), (vu.prenom or "").strip()]))

            # 2) sinon: le garant s'il existe
            if not owner and contrat.garant:
                g: Garant = contrat.garant
                owner = " ".join(filter(None, [(g.nom or "").strip(), (g.prenom or "").strip()]))

            # 3) fallback éventuel (ex: VIN)
            if not owner and assoc and assoc.moto_valide:
                vin = (assoc.moto_valide.vin or "").strip()
                if vin:
                    owner = vin  # ou f"Proprio VIN {vin}"

            if owner:
                # évite les conditions de course et n’écrase pas si déjà rempli
                ContratBatterie.objects.filter(pk=batt.pk, proprietaire__isnull=True).update(proprietaire=owner)
                # si la colonne permet vide mais pas null:
                ContratBatterie.objects.filter(pk=batt.pk, proprietaire="").update(proprietaire=owner)

        return contrat


# -------------------------------------------------------------------
# UPDATE / PATCH
# -------------------------------------------------------------------
class ContractDriverUpdateSerializer(serializers.ModelSerializer):
    contrat_physique_chauffeur = serializers.FileField(required=False, allow_null=True)
    contrat_physique_batt = serializers.FileField(required=False, allow_null=True)
    contrat_physique_moto_garant = serializers.FileField(required=False, allow_null=True)
    contrat_physique_batt_garant = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = ContratChauffeur
        fields = [
            "reference_contrat",
            "montant_total", "montant_paye", "montant_restant",
             "montant_par_paiement",
            "date_signature", "date_debut", "date_fin",
            "duree_jour",
            "statut", "montant_engage",
            "contrat_physique_chauffeur",
            "contrat_physique_batt",
            "contrat_physique_moto_garant",
            "contrat_physique_batt_garant",
            "jour_conge_total",
            "jour_conge_utilise",
            "jour_conge_restant",
            "association_user_moto",  # ✅ writable FK for updates too
            "contrat_batt",
            "garant",
            "regle_penalite",
        ]
        read_only_fields = ("duree_jour", "date_fin", "montant_restant")

    def validate_statut(self, value):
        return _map_choice(value, field_name="statut")

    def validate_frequence_paiement(self, value):
        return _map_choice(value, field_name="frequence_paiement")

    def validate(self, attrs):
        inst = self.instance
        today = timezone.now().date()

        # ✅ clamp date_signature on update as well
        sig = attrs.get("date_signature", getattr(inst, "date_signature", None))
        if not sig or sig > today:
            attrs["date_signature"] = today

        mt = attrs.get("montant_total", inst.montant_total)
        mp = attrs.get("montant_paye", inst.montant_paye)
        mpp = attrs.get("montant_par_paiement", getattr(inst, "montant_par_paiement", 3500) or 3500)
        d_debut = attrs.get("date_debut", inst.date_debut)

        # montant_restant always recomputed unless explicitly provided
        if "montant_restant" not in attrs:
            attrs["montant_restant"] = (mt or 0) - (mp or 0)

        # recompute date_fin & duree_jour from updated values
        date_fin, days = _compute_fin_and_duration(
            date_debut=d_debut,
            montant_total=mt or 0,
            montant_paye=mp or 0,
            montant_par_paiement=mpp,
        )
        attrs["date_fin"] = date_fin

        field = ContratChauffeur._meta.get_field("duree_jour")
        attrs["duree_jour"] = _encode_days_as_datetime(days) if isinstance(field, dj_models.DateTimeField) else days

        # congés restant
        jtot = attrs.get("jour_conge_total", inst.jour_conge_total or 0)
        juse = attrs.get("jour_conge_utilise", inst.jour_conge_utilise or 0)
        attrs["jour_conge_restant"] = (jtot or 0) - (juse or 0)

        # safety
        if mt is not None and mp is not None and mp > mt:
            raise serializers.ValidationError("Le montant payé ne peut pas dépasser le montant total.")
        return attrs

    def update(self, instance, validated_data):
        # File replacements (keep same pattern as battery)
        for f in [
            "contrat_physique_chauffeur",
            "contrat_physique_batt",
            "contrat_physique_moto_garant",
            "contrat_physique_batt_garant",
        ]:
            new_file = validated_data.get(f)
            if new_file:
                old = getattr(instance, f, None)
                if old:
                    old.delete(save=False)
                setattr(instance, f, new_file)

        # other fields
        for attr, value in validated_data.items():
            if attr not in {
                "contrat_physique_chauffeur",
                "contrat_physique_batt",
                "contrat_physique_moto_garant",
                "contrat_physique_batt_garant",
            }:
                setattr(instance, attr, value)
        instance.save()
        return instance


class ContractDriverStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContratChauffeur
        fields = ("id", "statut", "montant_restant")
        read_only_fields = fields
