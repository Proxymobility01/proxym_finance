from django.urls import path
from .views import LeasePaymentAPIView, LeasePaymentListAPIView, LeasePaymentDetailAPIView, LeaseSuiviAPIView

urlpatterns = [
    path("lease/pay", LeasePaymentAPIView.as_view(), name="lease-pay"),  # POST
    path("lease/payments", LeasePaymentListAPIView.as_view(), name="lease-payments"),
    path("lease/suivi",LeaseSuiviAPIView.as_view(), name="lease-suivi"),
    path("lease/payments/<int:pk>", LeasePaymentDetailAPIView.as_view(), name="lease-payment-detail"),  # GET one
]
