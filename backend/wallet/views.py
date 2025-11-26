from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging

from wallet.serializers import WalletSerializer, DepositInitSerializer
from wallet.services.statut_service import StatutService
# ⬇️ Utiliser le service Cash-Out (pas DepositService)
from wallet.services.cashout_service import CashoutService
from wallet.services.maviance_api_service import MavianceAPIService



logger = logging.getLogger("wallet")


class WalletStatutAPIView(APIView):
    """
    PUT /api/wallets/<pk>/<action>/
    Exemple:
      /api/wallets/15/activer/
      /api/wallets/15/bloquer/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int, action: str):
        try:
            wallet = StatutService.changer_statut(pk, action)
            return Response({
                "success": True,
                "message": f"✅ Le compte {wallet.unique_id} a été mis à jour ({wallet.statut}).",
                "data": WalletSerializer(wallet).data
            })
        except ValueError as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[WalletStatutAPIView] Error: {e}")
            return Response({"success": False, "message": str(e)}, status=status.HTTP_404_NOT_FOUND)


# ======================================================
# 💳 INITIER UN CASH-OUT (débit du client)
# ======================================================
class WalletCashoutInitAPIView(APIView):
    """
    POST /api/wallets/<wallet_id>/cashout/

    Headers:
      Authorization: Bearer <JWT>
      Idempotency-Key: <UUID/ULID>  (obligatoire)

    Body:
      {
        "amount": "5000.00",
        "channel": "mtn|orange",
        "msisdn": "6XXXXXXX"     # 9 derniers chiffres conseillés
      }
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, wallet_id: int):
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response(
                {"detail": "L’en-tête 'Idempotency-Key' est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # On réutilise ton serializer (amount, channel, msisdn)
        serializer = DepositInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            logger.info(f"[CashoutInit] Start wallet={wallet_id}, data={data}")

            # ⚡ Lancement du flux Cash-Out (GET /cashout -> payItemId, POST /quotestd, POST /collectstd)
            result = CashoutService.initiate(
                wallet_id=wallet_id,
                amount=data["amount"],
                channel=data["channel"],
                msisdn=data["msisdn"],
                idempotency_key=idempotency_key
            )

            logger.info(f"[CashoutInit] Result: {result}")

            return Response({
                "success": True,
                "message": "✅ Cash-Out initié avec succès.",
                "wallet_id": wallet_id,
                "quoteId": result.get("quoteId"),
                "trid": result.get("trid"),
                "status": result.get("status", "PENDING"),
                "ptn": result.get("ptn"),
                "reference_proxym": result.get("reference_proxym"),
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"[CashoutInit] Exception: {e}")
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ======================================================
# 🔍 VÉRIFIER L’ÉTAT DU CASH-OUT
# ======================================================
class WalletCashoutVerifyAPIView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        trid = request.query_params.get("trid")
        if not trid:
            return Response({"error": "Paramètre 'trid' manquant"}, status=400)

        logger.info(f"[CashoutVerify] trid={trid}")

        try:
            data = MavianceAPIService.verify_transaction(trid)
            logger.info(f"[Cashout] Vérification réponse: {data}")

            # ✅ Smobilpay renvoie parfois une liste
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            return Response(
                {
                    "success": True,
                    "message": "🧾 Statut du Cash-Out vérifié avec succès.",
                    "status": data.get("status"),
                    "ptn": data.get("ptn"),
                    "amount": data.get("priceLocalCur"),
                    "timestamp": data.get("timestamp"),
                    "trid": data.get("trid"),
                },
                status=200,
            )

        except Exception as e:
            logger.error(f"[CashoutVerify] Exception: {e}")
            return Response({"error": str(e)}, status=500)
