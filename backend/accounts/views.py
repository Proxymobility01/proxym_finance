from django.shortcuts import render
from rest_framework import permissions, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from accounts.models import CustomUser
from accounts.serializers import UserLiteSerializer, IsAdminRoleOrSuperuser, CustomTokenObtainPairSerializer


# Create your views here.
class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.select_related("role").all()
    serializer_class = UserLiteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]