# wallet/serializers.py
from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import Wallet, Transaction

class WalletSerializer(serializers.ModelSerializer):
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ["id","unique_id","type","solde","statut","device","created_at","updated_at","recent_transactions"]
        read_only_fields = ["unique_id","solde","created_at","updated_at"]

    def get_recent_transactions(self, obj):
        tx = obj.transactions_maviance.all().order_by("-created_at")[:5]
        return TransactionSerializer(tx, many=True).data

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id","reference_proxym","reference","type","montant","statut",
            "s3p_quote_id","s3p_trid","channel","initiated_at","completed_at"
        ]

class DepositInitSerializer(serializers.Serializer):
    amount = serializers.CharField()
    channel = serializers.ChoiceField(choices=["mtn","orange"])
    msisdn = serializers.CharField(min_length=9, max_length=20)

    def validate_amount(self, value):
        try:
            d = Decimal(value)
        except InvalidOperation:
            raise serializers.ValidationError("Montant invalide.")
        if d <= 0:
            raise serializers.ValidationError("Le montant doit être > 0.")
        return str(d.quantize(Decimal("0.01")))
