from rest_framework import serializers
from .models import PaiementLease

from penalite.models import Penalite

class LeasePaymentLiteSerializer(serializers.ModelSerializer):
    # Champs calculés / aplatis
    contrat_id = serializers.IntegerField(write_only=True)
    date_paiement_concerne = serializers.DateField(write_only=True, required=True)
    date_limite_paiement = serializers.DateField(write_only=True, required=True)
    chauffeur = serializers.SerializerMethodField(read_only=True)
    moto_unique_id = serializers.SerializerMethodField(read_only=True)
    moto_vin = serializers.SerializerMethodField(read_only=True)
    station_paiement = serializers.SerializerMethodField(read_only=True)
    paye_par = serializers.SerializerMethodField(read_only=True)
    statut_paiement = serializers.SerializerMethodField(read_only=True)
    statut_penalite = serializers.SerializerMethodField(read_only=True)
    source = serializers.SerializerMethodField(read_only=True)
    date_concernee = serializers.DateField(read_only=True)
    date_limite = serializers.DateField(read_only=True)

    class Meta:
        model = PaiementLease
        fields = [
            "id",
            "contrat_id",
            "chauffeur",
            "moto_unique_id",
            "moto_vin",
            "montant_moto",
            "montant_batt",
            "montant_total",
            "date_paiement_concerne",
            "date_limite_paiement",
            "date_concernee",
            "date_limite",
            "methode_paiement",
            "station_paiement",
            "statut_paiement",
            "statut_penalite",
            "paye_par",
            "created",
            "source",            # "PAYE"
        ]

    # ---- getters ----
    def get_chauffeur(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        vu = getattr(assoc, "validated_user", None) if assoc else None
        if vu:
            nom = (vu.nom or "").strip()
            prenom = (vu.prenom or "").strip()
            full = f"{nom} {prenom}".strip()
            return full or None
        return None

    def get_moto_unique_id(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        mv = getattr(assoc, "moto_valide", None) if assoc else None
        return getattr(mv, "moto_unique_id", None) if mv else None

    def get_moto_vin(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        mv = getattr(assoc, "moto_valide", None) if assoc else None
        return getattr(mv, "vin", None) if mv else None

    def get_station_paiement(self, obj):
        ua = getattr(obj, "user_agence", None)
        # adapte au champ réel (name / label / code)
        return getattr(ua, "name", None) or getattr(ua, "code", None) if ua else None

    def get_paye_par(self, obj):
        u = getattr(obj, "employe", None)
        if not u:
            return None
        # adapte si tu as first_name/last_name
        full = (" ".join(x for x in [getattr(u, "first_name", ""), getattr(u, "last_name", "")] if x).strip()) or getattr(u, "username", None)
        return full or None

    def get_statut_paiement(self, obj):
        # côté paiements, c'est PAYE
        return "PAYE"

    def get_statut_penalite(self, obj):
        return None

    def get_source(self, obj):
        return "PAYE"



from rest_framework import serializers
from penalite.models import Penalite
class LeaseNonPayeLiteSerializer(serializers.ModelSerializer):
    chauffeur = serializers.SerializerMethodField()
    moto_unique_id = serializers.SerializerMethodField()
    moto_vin = serializers.SerializerMethodField()

    montant_moto = serializers.SerializerMethodField()   # "-3500.00"
    montant_batt = serializers.SerializerMethodField()   # "-500.00"
    montant_total = serializers.SerializerMethodField()  # -4000.0 (float)

    date_concernee = serializers.DateField(source="date_paiement_manquee", allow_null=True)
    date_limite = serializers.SerializerMethodField()

    methode_paiement = serializers.SerializerMethodField()
    station_paiement = serializers.SerializerMethodField()
    statut_paiement = serializers.SerializerMethodField()
    statut_penalite = serializers.SerializerMethodField()

    paye_par = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta:
        model = Penalite
        fields = [
            "id",
            "chauffeur",
            "moto_unique_id",
            "moto_vin",
            "montant_moto",
            "montant_batt",
            "montant_total",
            "date_concernee",
            "date_limite",
            "methode_paiement",
            "station_paiement",
            "statut_paiement",
            "statut_penalite",
            "paye_par",
            "source",   # "NON_PAYE"
        ]

    # -------- enrichissements --------
    def _q2(self, val):
        from decimal import Decimal, ROUND_HALF_UP
        try:
            d = Decimal(val or 0)
        except Exception:
            d = Decimal(0)
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_chauffeur(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        vu = getattr(assoc, "validated_user", None) if assoc else None
        if vu:
            nom = (vu.nom or "").strip()
            prenom = (vu.prenom or "").strip()
            full = f"{nom} {prenom}".strip()
            return full or None
        return None

    def get_moto_unique_id(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        mv = getattr(assoc, "moto_valide", None) if assoc else None
        return getattr(mv, "moto_unique_id", None) if mv else None

    def get_moto_vin(self, obj):
        assoc = getattr(obj.contrat_chauffeur, "association_user_moto", None)
        mv = getattr(assoc, "moto_valide", None) if assoc else None
        return getattr(mv, "vin", None) if mv else None

    def get_montant_moto(self, obj) -> str:
        contrat = obj.contrat_chauffeur
        moto_due = -self._q2(getattr(contrat, "montant_par_paiement", 0))
        return f"{moto_due:.2f}"

    def get_montant_batt(self, obj) -> str:
        cb = getattr(obj.contrat_chauffeur, "contrat_batt", None)
        batt_due = -self._q2(getattr(cb, "montant_par_paiement", 0) if cb else 0)
        return f"{batt_due:.2f}"

    def get_montant_total(self, obj) -> float:
        from decimal import Decimal, ROUND_HALF_UP
        moto = Decimal(self.get_montant_moto(obj))
        batt = Decimal(self.get_montant_batt(obj))
        total = (moto + batt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(total)

    def get_date_limite(self, obj):
        if getattr(obj, "date_limite_reference", None):
            return obj.date_limite_reference
        cc = getattr(obj, "contrat_chauffeur", None)
        if cc and getattr(cc, "date_limite", None):
            return cc.date_limite
        return obj.date_paiement_manquee

    def get_methode_paiement(self, obj):
        return None

    def get_station_paiement(self, obj):
        return None

    def get_statut_paiement(self, obj):
        return "NON_PAYE"

    def get_statut_penalite(self, obj):
        s = getattr(obj, "statut_penalite", None)
        return s.lower() if isinstance(s, str) else s

    def get_paye_par(self, obj):
        return None

    def get_source(self, obj):
        return "NON_PAYE"


