from django.urls import path
from .views import (
    ContratBatterieListCreateView,
    ContratBatterieDetailView,
    ContractChauffeurListCreateView,
    ContractChauffeurDetailView, ModifierStatutContratAPIView,
    ContratChauffeurUpdateAPIView,
)

urlpatterns = [
    # Battery contracts
    path("contrats-batteries", ContratBatterieListCreateView.as_view(), name="contrat-batterie-list-create"),
    path("contrats-batteries/<int:pk>", ContratBatterieDetailView.as_view(), name="contrat-batterie-detail"),
    path("contrats-chauffeurs", ContractChauffeurListCreateView.as_view(), name="contrat-chauffeur-list-create"),
    path("contrats-chauffeur/<int:pk>/update/", ContratChauffeurUpdateAPIView.as_view(), name="contrat-chauffeur-update"),
    path("contrats-chauffeurs/<int:pk>", ContractChauffeurDetailView.as_view(), name="contrat-chauffeur-detail"),
    path('contrats-chauffeurs/<int:pk>/changer-statut/', ModifierStatutContratAPIView.as_view(), name='changer-statut-contrat'),
]
