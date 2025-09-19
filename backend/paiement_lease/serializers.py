from rest_framework import serializers
from .models import PaiementLease

class LeasePaymentSerializer(serializers.ModelSerializer):
    contrat_id = serializers.IntegerField(write_only=True)
    date_paiement_concerne = serializers.DateField(write_only=True)
    date_limite_paiement = serializers.DateField(write_only=True)
    reference_transaction = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )  # 👈 pas obligatoire

    # Champs enrichis (lecture seule)
    chauffeur = serializers.SerializerMethodField()
    moto = serializers.SerializerMethodField()

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
            "reference_transaction",
            "type_contrat",
            "contrat_chauffeur",
            "date_concernee",
            "date_limite",
            "statut",
            "employe",
            "user_agence",
            "created",
            "chauffeur",   # 👈 ajouté
            "moto",        # 👈 ajouté
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
            "chauffeur",
            "moto",
        ]

    def get_chauffeur(self, obj):
        assoc = obj.contrat_chauffeur.association_user_moto
        if assoc and assoc.validated_user:
            vu = assoc.validated_user
            return {
                "id": vu.id,
                "user_unique_id": vu.user_unique_id,
                "nom": vu.nom,
                "prenom": vu.prenom,
                "email": vu.email,
                "phone": getattr(vu, "phone", None),
            }
        return None

    def get_moto(self, obj):
        assoc = obj.contrat_chauffeur.association_user_moto
        if assoc and assoc.moto_valide:
            mv = assoc.moto_valide
            return {
                "id": mv.id,
                "moto_unique_id": getattr(mv, "moto_unique_id", None),
                "vin": getattr(mv, "vin", None),
                "gps_imei": getattr(mv, "gps_imei", None),
                "model": getattr(mv, "model", None),
            }
        return None
