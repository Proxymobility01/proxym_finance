from django.urls import path

from paiement_lease.views import  PaiementLeaseAPIView, \
    LeaseCombinedListAPIView, LeaseCombinedExportXLSX, LeaseCombinedExportCSV, CalendrierPaiementsAPIView


urlpatterns = [
    path("lease/pay", PaiementLeaseAPIView.as_view(), name="lease-pay"),
    path("lease/combined", LeaseCombinedListAPIView.as_view(), name="lease-combined"),
    path("lease/combined/export/xlsx", LeaseCombinedExportXLSX.as_view(), name="lease-combined-export-excel"),
    path("lease/combined/export/csv", LeaseCombinedExportCSV.as_view(), name="lease-combined-export-csv"),
    path("lease/paiements/calendrier/", CalendrierPaiementsAPIView.as_view(), name="calendrier-paiements"),

]
