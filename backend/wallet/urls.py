# wallet/urls.py
from django.urls import path
from wallet.views import (
    WalletStatutAPIView,
    WalletCashoutInitAPIView,
    WalletCashoutVerifyAPIView,
)

urlpatterns = [
    # 💸 Cash-Out
    path("wallets/<int:wallet_id>/cashout/", WalletCashoutInitAPIView.as_view(), name="wallet-cashout-init"),
    path("wallets/cashout/verify/", WalletCashoutVerifyAPIView.as_view(), name="wallet-cashout-verify"),

    # ⚙️ Gestion du statut du portefeuille
    path("wallets/<int:pk>/<str:action>/", WalletStatutAPIView.as_view(), name="wallet-statut"),
]
