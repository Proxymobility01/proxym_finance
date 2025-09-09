from django.urls import path
from .views import GarantListCreateView, GarantDetailView

urlpatterns = [
    path("garants/", GarantListCreateView.as_view(), name="garant-list-create"),
    path("garants/<int:pk>/", GarantDetailView.as_view(), name="garant-detail"),
]
