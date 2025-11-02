# wallet/urls.py
from django.urls import path
from .views import WalletStatutAPIView

urlpatterns = [
    path('wallets/<int:pk>/<str:action>/', WalletStatutAPIView.as_view(), name='wallet-statut'),
]
