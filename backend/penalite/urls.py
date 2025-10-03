# penalite/urls.py
from django.urls.conf import path, include
from rest_framework.routers import DefaultRouter
from .views import PenaliteViewSet, PaiementPenaliteViewSet, AnnulerPenaliteAPIView

router = DefaultRouter()
router.register(r"penalites", PenaliteViewSet, basename="penalite")
router.register(r"paiements-penalites", PaiementPenaliteViewSet, basename="paiement-penalite")
urlpatterns = [
    path("penalites/<int:pk>/annuler", AnnulerPenaliteAPIView.as_view(), name="penalite-annuler"),
    path("", include(router.urls)),
]
