# app_legacy/urls.py
from django.urls import path
from .views import AssociationSummaryView

urlpatterns = [
    path("legacy/associations/<int:pk>/summary", AssociationSummaryView.as_view(), name="association-summary"),
]
