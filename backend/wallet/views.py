from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from wallet.serializers import WalletSerializer
from wallet.services.statut_service import StatutService


class WalletStatutAPIView(APIView):
    """
    🔐 API REST sécurisée pour la gestion des statuts des Wallets.
    ----------------------------------------------------------------
    Cette API requiert une authentification JWT.
    Seuls les utilisateurs authentifiés peuvent accéder à ces endpoints.

    Routes :
      - POST /api/wallets/<id>/bloquer/
      - POST /api/wallets/<id>/suspendre/
      - POST /api/wallets/<id>/activer/
    """

    # 🧱 Authentification & Permissions (comme tes autres API)
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int, action: str):
        """
        Change le statut d’un Wallet selon l’action demandée.
        L’action est déléguée au StatutService.
        """
        try:
            wallet = StatutService.changer_statut(pk, action)
            serializer = WalletSerializer(wallet)

            return Response({
                "success": True,
                "message": f"✅ Le compte {wallet.unique_id} a été mis à jour ({wallet.statut}).",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_404_NOT_FOUND)
