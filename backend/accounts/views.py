import logging

from django.shortcuts import render
from rest_framework import permissions, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from accounts.models import CustomUser
from accounts.serializers import UserLiteSerializer, CustomTokenObtainPairSerializer
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

# Create your views here.
class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.select_related("role").all()
    serializer_class = UserLiteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]




logger = logging.getLogger(__name__)

class LogoutView(APIView):

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # ✅ Ajoute à la table blacklist
            logger.info(f"✅ Token black-listé avec succès : {token}")
            return Response(
                {"detail": "Déconnexion réussie."},
                status=status.HTTP_205_RESET_CONTENT
            )

        except TokenError as e:
            # Token déjà blacklisté ou invalide
            logger.warning(f"⚠️ Token invalide ou déjà expiré : {str(e)}")
            return Response(
                {"detail": "Token invalide ou déjà expiré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"❌ Erreur lors du logout : {e}")
            return Response(
                {"detail": "Erreur serveur lors de la déconnexion."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
