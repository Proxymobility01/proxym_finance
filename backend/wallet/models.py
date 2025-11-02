from django.db import models
from django.utils import timezone


# ============================================================
#       BASE COMMUNE : AJOUT DES CHAMPS created_at / updated_at
# ============================================================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # 👈 Ne crée pas de table pour ce modèle


# ============================================================
#                        WALLET
# ============================================================

from django.db import models
from django.utils import timezone


# ============================================================
#       BASE COMMUNE : created_at / updated_at
# ============================================================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ============================================================
#                        WALLET
# ============================================================

class Wallet(TimeStampedModel):
    TYPE_CHOICES = [
        ("chauffeur", "Chauffeur"),
        ("proxym", "Proxym"),
        ("externe", "Externe"),
    ]

    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("bloque", "Bloqué"),
        ("suspendu", "Suspendu"),
    ]

    unique_id = models.CharField(
    max_length=10,
    unique=True,
    editable=False,
    db_index=True,
    null=True,         
    blank=True
)


    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    solde = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="actif")
    device = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        """
        Génère automatiquement un identifiant unique du type WPX001, WPX002, ...
        au moment de la création.
        """
        if not self.unique_id:
            last_wallet = Wallet.objects.order_by("-id").first()
            if last_wallet and last_wallet.unique_id and last_wallet.unique_id.startswith("WPX"):
                # extraire le numéro et incrémenter
                num = int(last_wallet.unique_id.replace("WPX", "")) + 1
            else:
                num = 1
            self.unique_id = f"WPX{num:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.unique_id} | {self.type.upper()} | {self.solde} XAF"

    class Meta:
        db_table = "wallet"
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"



# ============================================================
#                    TRANSACTION MAVIANCE
# ============================================================

class Transaction(TimeStampedModel):
    TYPE_CHOICES = [
        ("depot", "Dépôt"),
        ("retrait", "Retrait"),
    ]
    STATUT_CHOICES = [
        ("pending", "En attente"),
        ("success", "Succès"),
        ("failed", "Échec"),
    ]

    reference_proxym = models.CharField(max_length=50, unique=True, editable=False,null=True)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions_maviance")
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    frais_transaction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="pending")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    initiated_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.reference_proxym:
            today = datetime.now().strftime("%Y%m%d")
            count_today = Transaction.objects.filter(
                created_at__date=datetime.now().date()
            ).count() + 1
            self.reference_proxym = f"PXM{today}{count_today:02d}"
        super().save(*args, **kwargs)

    class Meta:
        db_table = "transaction"

    def __str__(self):
        return f"[{self.reference_proxym}] {self.wallet} - {self.montant} XAF ({self.type})"



# ============================================================
#                    TRANSACTION PROXYM
# ============================================================


class TransactionProxym(TimeStampedModel):
    TYPE_CHOICES = [
        ("swap", "Swap"),
        ("lease", "Lease"),
        ("penalite", "Pénalité"),
    ]
    STATUT_CHOICES = [
        ("pending", "En attente"),
        ("success", "Succès"),
        ("failed", "Échec"),
    ]

    reference = models.CharField(max_length=50, unique=True, editable=False,null=True)
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="pending")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions_proxym")

    def save(self, *args, **kwargs):
        if not self.reference:
            today = datetime.now().strftime("%Y%m%d")
            count_today = TransactionProxym.objects.filter(
                created_at__date=datetime.now().date()
            ).count() + 1
            self.reference = f"PX{today}{count_today:02d}"
        super().save(*args, **kwargs)

    class Meta:
        db_table = "transaction_proxym"

    def __str__(self):
        return f"{self.reference} | {self.type.upper()} | {self.montant} XAF"


# ============================================================
#                    TRANSACTION EXTERNE (P2P)
# ============================================================


class TransactionExterne(TimeStampedModel):
    STATUT_CHOICES = [
        ("pending", "En attente"),
        ("success", "Succès"),
        ("failed", "Échec"),
    ]

    reference = models.CharField(max_length=50, unique=True, editable=False,null=True)
    wallet_envoyeur = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="envois")
    wallet_receveur = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="receptions")
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="pending")
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            today = datetime.now().strftime("%Y%m%d")
            count_today = TransactionExterne.objects.filter(
                created_at__date=datetime.now().date()
            ).count() + 1
            self.reference = f"PXC{today}{count_today:02d}"
        super().save(*args, **kwargs)

    class Meta:
        db_table = "transaction_externe"

    def __str__(self):
        return f"{self.reference} | Transfert {self.montant} XAF de {self.wallet_envoyeur} → {self.wallet_receveur}"
    
# ============================================================
#                    JOURNAL TRANSACTION (AUDIT)
# ============================================================

class JournalTransaction(TimeStampedModel):
    TYPE_CHOICES = [
        ("maviance", "Maviance"),
        ("proxym", "Proxym"),
        ("chauffeur", "Chauffeur"),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    id_transaction_maviance = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    id_transaction_proxym = models.ForeignKey(TransactionProxym, on_delete=models.SET_NULL, null=True, blank=True)
    id_transaction_chauffeur = models.ForeignKey(TransactionExterne, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "journal_transaction"

    def __str__(self):
        return f"Journal [{self.type}]"


# ============================================================
#                    SAUVEGARDE TRANSACTIONS (LOG API)
# ============================================================

class SauvegardeTransaction(TimeStampedModel):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="sauvegardes")
    reference = models.CharField(max_length=100)
    request_payload = models.JSONField(blank=True, null=True)
    response_payload = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "sauvegarde_transactions"

    def __str__(self):
        return f"Sauvegarde {self.reference}"
