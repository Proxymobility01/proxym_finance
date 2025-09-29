# penalite/serializers.py
from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from uuid import uuid4
from django.db import transaction
from .models import Penalite, PaiementPenalite, StatutPenalite


class PenaliteListSerializer(serializers.ModelSerializer):
    # infos contrat
    contrat_id = serializers.IntegerField(source="contrat_chauffeur.id", read_only=True)
    reference_contrat = serializers.CharField(source="contrat_chauffeur.reference_contrat", read_only=True)
    chauffeur = serializers.SerializerMethodField()

    class Meta:
        model = Penalite
        fields = [
            "id",
            "type_penalite",
            "montant_penalite",
            "motif_penalite",
            "description",
            "statut_penalite",
            "date_paiement_manquee",
            "montant_paye",
            "montant_restant",
            # infos contrat
            "contrat_id",
            "reference_contrat",
            "chauffeur",
        ]

    def get_chauffeur(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        if assoc and getattr(assoc, "validated_user", None):
            vu = assoc.validated_user
            nom = (vu.nom or "").strip()
            prenom = (vu.prenom or "").strip()
            full = f"{nom} {prenom}".strip()
            return full or None
        return None




def _next_reference() -> str:
    now = timezone.now()
    yyyymm = f"{now.year}{now.month:02d}"
    return f"PP-{yyyymm}-{uuid4().hex[:5].upper()}"


class PaiementPenaliteCreateSerializer(serializers.ModelSerializer):
    # on accepte penalite_id en entrée
    penalite_id = serializers.PrimaryKeyRelatedField(
        source="penalite",
        queryset=Penalite.objects.all(),
        write_only=True,
        required=True,
    )

    # read-only renvoyés à la création
    reference = serializers.CharField(read_only=True)

    class Meta:
        model = PaiementPenalite
        fields = [
            "id",
            "reference",
            "penalite_id",             # in
            "montant",                 # in
            "methode_paiement",        # in
            "reference_transaction",   # in (optionnel)
            "user_agence",             # in (optionnel)
            "created", "updated",      # out (TimeStampedModel)
        ]
        read_only_fields = ("id", "reference", "created", "updated")

    def validate(self, attrs):
        penalite: Penalite = attrs["penalite"]
        montant: Decimal = attrs.get("montant") or Decimal("0")

        # déjà payée ?
        if getattr(penalite, "statut_penalite", None) == StatutPenalite.PAYE:
            raise serializers.ValidationError(
                {"penalite_id": "Cette pénalité est déjà soldée."}
            )

        if montant <= 0:
            raise serializers.ValidationError({"montant": "Le montant doit être > 0."})

        # Sur-paiement interdit
        restant = penalite.montant_restant or Decimal("0")
        if montant > restant:
            raise serializers.ValidationError(
                {"montant": f"Le montant dépasse le restant ({restant})."}
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # verrouille la pénalité le temps de l'opération (évite doubles écritures)
        penalite = (
            Penalite.objects.select_for_update()
            .select_related("contrat_chauffeur")
            .get(pk=validated_data["penalite"].pk)
        )

        montant: Decimal = validated_data["montant"]

        # référence auto
        validated_data["reference"] = _next_reference()

        # employé depuis le request.user si dispo
        request = self.context.get("request")
        if request and getattr(request, "user", None) and request.user.is_authenticated:
            validated_data["employe"] = request.user

        paiement = PaiementPenalite.objects.create(**validated_data)

        # --- Mise à jour de la pénalité
        penalite.montant_paye = (penalite.montant_paye or Decimal("0")) + montant
        penalite.montant_restant = (penalite.montant_penalite or Decimal("0")) - penalite.montant_paye

        if penalite.montant_restant <= 0:
            penalite.montant_restant = Decimal("0")
            penalite.statut_penalite = StatutPenalite.PAYE
        elif penalite.montant_paye > 0:
            penalite.statut_penalite = StatutPenalite.PARTIELLEMENT_PAYE
        else:
            penalite.statut_penalite = StatutPenalite.NON_PAYE

        penalite.save(update_fields=["montant_paye", "montant_restant", "statut_penalite", "updated"])

        return paiement