from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import ContratChauffeur
from app_legacy.models import AssociationUserMoto
from garant.models import Garant

class ContractCreateSerializer(serializers.Serializer):
    association_user_moto_id = serializers.IntegerField()
    garant_id = serializers.IntegerField()
    reference_contrat = serializers.CharField(required=False, allow_blank=True)
    frequence_paiement = serializers.CharField()
    montant_par_paiement = serializers.DecimalField(max_digits=14, decimal_places=2)
    montant_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    date_debut = serializers.DateField()
    date_fin = serializers.DateTimeField(required=False)
    montant_caution_batt = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    montant_engage = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)

    def validate(self, attrs):
        if not AssociationUserMoto.objects.filter(id=attrs["association_user_moto_id"]).exists():
            raise serializers.ValidationError("association_user_moto_id not found.")
        if not Garant.objects.filter(id=attrs["garant_id"]).exists():
            raise serializers.ValidationError("garant_id not found.")
        if attrs["frequence_paiement"].lower() not in ("daily", "weekly", "monthly"):
            raise serializers.ValidationError("frequence_paiement must be: daily|weekly|monthly")
        return attrs

    @transaction.atomic
    def create(self, data):
        now = timezone.now()
        c = ContratChauffeur(
            created=now, updated=now,
            association_user_moto_id=data["association_user_moto_id"],
            garant_id=data["garant_id"],
            reference_contrat=data.get("reference_contrat") or None,
            frequence_paiement=data["frequence_paiement"],
            montant_par_paiement=data["montant_par_paiement"],
            montant_total=data["montant_total"],
            montant_paye=0, montant_restant=data["montant_total"],
            date_debut=data["date_debut"],
            date_fin=data.get("date_fin"),
            statut="DRAFT",
            montant_caution_batt=data.get("montant_caution_batt"),
            montant_engage=data.get("montant_engage"),
        )
        c.full_clean()
        c.save(force_insert=True)
        return c

class ContractActivateSerializer(serializers.Serializer):
    def update(self, instance: ContratChauffeur, validated_data):
        instance.statut = "ACTIVE"
        instance.updated = timezone.now()
        instance.full_clean()
        instance.save(update_fields=["statut", "updated"])
        return instance
