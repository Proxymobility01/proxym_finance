from django.urls import path

from paiement_lease.views import PaiementLeaseAPIView, \
    LeaseCombinedListAPIView, LeaseCombinedExportXLSX, LeaseCombinedExportCSV, LeaseCombinedExportDOCX
from paiement_lease.views import  PaiementLeaseAPIView, \
    LeaseCombinedListAPIView, LeaseCombinedExportXLSX, LeaseCombinedExportCSV
from .views import calendrier_paiements_contrat

urlpatterns = [
    path("lease/pay", PaiementLeaseAPIView.as_view(), name="lease-pay"),
    path("lease/combined", LeaseCombinedListAPIView.as_view(), name="lease-combined"),
    path("lease/combined/export/xlsx", LeaseCombinedExportXLSX.as_view(), name="lease-combined-export-excel"),
    path("lease/combined/export/csv", LeaseCombinedExportCSV.as_view(), name="lease-combined-export-csv"),
    path("lease/combined/export/docx", LeaseCombinedExportDOCX.as_view(), name="lease-combined-export-docx"),
    path("paiements/calendrier/<int:contrat_id>", calendrier_paiements_contrat, name="calendrier-paiements-contrat"),

]
