from rest_framework import serializers
from .models import PaiementLease

class LeasePaymentSerializer(serializers.ModelSerializer):
    contrat_id = serializers.IntegerField(write_only=True)
    date_paiement_concerne = serializers.DateField(write_only=True)
    date_limite_paiement = serializers.DateField(write_only=True)
    reference_transaction = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )  # 👈 pas obligatoire

    class Meta:
        model = PaiementLease
        fields = [
            "id",
            "reference_paiement",
            "montant_moto",
            "montant_batt",
            "montant_total",
            "date_paiement",
            "methode_paiement",
            "reference_transaction",  # 👈 optionnel
            "type_contrat",
            "contrat_chauffeur",
            "date_concernee",
            "date_limite",
            "statut",
            "employe",
            "user_agence",
            "created",
            # write-only pour Postman
            "contrat_id",
            "date_paiement_concerne",
            "date_limite_paiement",
        ]
        read_only_fields = [
            "id",
            "reference_paiement",
            "date_paiement",
            "type_contrat",
            "statut",
            "created",
            "employe",
            "user_agence",
            "contrat_chauffeur",
            "date_concernee",
            "date_limite",
        ]
