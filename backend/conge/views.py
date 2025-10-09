from django.shortcuts import render

# Create your views here.
# conge/views.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import  IsAuthenticated
from rest_framework import viewsets
from .models import Conge
from .serializers import CongeCreateSerializer, CongeUpdateSerializer, CongeBaseSerializer

class CongeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = Conge.objects.all().select_related(
        "contrat", "contrat__association_user_moto__validated_user"
    )

    def get_serializer_class(self):
        if self.action == "create":
            return CongeCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CongeUpdateSerializer
        return CongeBaseSerializer

from django.http import HttpResponse

def trigger_error(request):
    # Ce code provoquera une erreur ZeroDivisionError qui sera capturée par Sentry.
    division_by_zero = 1 / 0
    return HttpResponse("This line will never be reached.")