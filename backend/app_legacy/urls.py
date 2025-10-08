from django.urls import path
from .views import AssociationSummaryView, AssociationSummaryListView

urlpatterns = [
    path("legacy/associations/<int:pk>/summary", AssociationSummaryView.as_view(), name="association-summary"),
    path("legacy/associations", AssociationSummaryListView.as_view(), name="association-summary-list"),
]
