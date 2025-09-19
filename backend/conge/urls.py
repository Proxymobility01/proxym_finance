# conge/urls.py
from rest_framework.routers import DefaultRouter
from .views import CongeViewSet

router = DefaultRouter()
router.register(r"conges", CongeViewSet, basename="conge")

urlpatterns = router.urls
