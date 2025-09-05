from django.urls import path
from .views import ContractCreateView, ContractActivateView

urlpatterns = [
    path("contracts", ContractCreateView.as_view(), name="contract-create"),
    path("contracts/<int:pk>/activate", ContractActivateView.as_view(), name="contract-activate"),
]
