from django.urls import path
from .views import (
    ContratBatterieListCreateView,
    ContratBatterieDetailView,
)

urlpatterns = [
    # Battery contracts
    path("contrats-batteries", ContratBatterieListCreateView.as_view(), name="contrat-batterie-list-create"),
    path("contrats-batteries/<int:pk>", ContratBatterieDetailView.as_view(), name="contrat-batterie-detail"),
]
