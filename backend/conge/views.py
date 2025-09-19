from django.shortcuts import render

# Create your views here.
# conge/views.py
from rest_framework import viewsets, mixins
from .models import Conge
from rest_framework.permissions import AllowAny
from .serializers import CongeSerializer


class CongeViewSet(mixins.CreateModelMixin,mixins.ListModelMixin,viewsets.GenericViewSet):


    queryset = Conge.objects.all().select_related(
        "contrat", "contrat__association_user_moto__validated_user"
    )
    serializer_class = CongeSerializer
    permission_classes = [AllowAny]
