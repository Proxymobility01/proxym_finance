from django.urls import path
from .views import GarantListCreateView

urlpatterns = [
    path("garants/", GarantListCreateView.as_view(), name="garant-list-create"),
]
