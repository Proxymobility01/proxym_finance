from django.urls import path
from .views import (
    ContratBatterieListCreateView,
    ContratBatterieDetailView,
    ContractChauffeurListCreateView,
    ContractChauffeurDetailView, ModifierStatutContratAPIView, ContratChauffeurRetrieveUpdateAPIView,
)

urlpatterns = [
    # Battery contracts
    path("contrats-batteries", ContratBatterieListCreateView.as_view(), name="contrat-batterie-list-create"),
    path("contrats-batteries/<int:pk>", ContratBatterieDetailView.as_view(), name="contrat-batterie-detail"),
    path("contrats-chauffeurs", ContractChauffeurListCreateView.as_view(), name="contrat-chauffeur-list-create"),
    path("contrats-chauffeurs/<int:pk>/", ContratChauffeurRetrieveUpdateAPIView.as_view(), name="contrat-chauffeur-detail-update"),
    path("contrats-chauffeurs/<int:pk>", ContractChauffeurDetailView.as_view(), name="contrat-chauffeur-detail"),
    path('contrats-chauffeurs/<int:pk>/changer-statut/', ModifierStatutContratAPIView.as_view(), name='changer-statut-contrat'),
]
