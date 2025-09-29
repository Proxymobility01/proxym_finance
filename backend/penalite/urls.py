# penalite/urls.py
from rest_framework.routers import DefaultRouter
from .views import PenaliteViewSet, PaiementPenaliteViewSet

router = DefaultRouter()
router.register(r"penalites", PenaliteViewSet, basename="penalite")  # GET list/retrieve
router.register(r"paiements-penalites", PaiementPenaliteViewSet, basename="paiement-penalite")
urlpatterns = router.urls
