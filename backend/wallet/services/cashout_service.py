import logging
import uuid
from wallet.services.maviance_api_service import MavianceAPIService

logger = logging.getLogger("wallet")


class CashoutService:
    """
    💸 Service de gestion du flux Cash-Out (débit du client)
    Smobilpay v3.0.5 — MTN / Orange / Express Union
    Fournit une réponse unifiée contenant:
        - wallet_id
        - quoteId
        - trid
        - ptn
        - paymentId
        - status
        - payItem details
    """

    # -------------------------------------------------------------------------
    @staticmethod
    def list_payment_options():
        """
        1️⃣ Lister les opérateurs / canaux disponibles pour le Cash-Out.
        """
        try:
            logger.info("[Cashout] Fetching list of available cashout options...")
            response = MavianceAPIService._request("GET", "/cashout")
            logger.info(f"[Cashout] Options disponibles: {response}")
            return response
        except Exception as e:
            logger.error(f"[Cashout] Erreur récupération options: {e}")
            raise Exception("Impossible de récupérer les opérateurs Cash-Out.")

    # -------------------------------------------------------------------------
    @staticmethod
    def initiate(wallet_id: int, amount: str, channel: str, msisdn: str, idempotency_key: str):
        """
        2️⃣ Initier un Cash-Out :
            - Trouve le bon payItemId selon le canal (MTN / Orange)
            - Crée un devis (quote)
            - Lance le collectstd (débit du client)
            - Retourne un JSON unifié avec toutes les infos
        """
        logger.info(f"[Cashout] INIT START wallet={wallet_id}, canal={channel}, tel={msisdn}")

        # 🔍 Obtenir la liste des services Cash-Out disponibles
        options = CashoutService.list_payment_options()

        pay_item = None
        for opt in options:
            if channel.lower() in opt["merchant"].lower():
                pay_item = opt
                break

        if not pay_item:
            raise Exception(f"⚠️ Canal inconnu ou non supporté : {channel}")

        logger.info(f"[Cashout] Canal={channel.upper()} PayItemId={pay_item['payItemId']}")

        # 💰 Créer le devis (quote)
        quote_resp = MavianceAPIService.create_quote(pay_item["payItemId"], float(amount))
        quote_id = quote_resp.get("quoteId")
        logger.info(f"[Cashout] Quote created ID={quote_id}")

        # 💸 Initier le collectstd (débit)
        trid = str(uuid.uuid4())[:8]
        collect_resp = MavianceAPIService.collect_payment(
            quote_id,
            {
                "phone": msisdn,
                "serviceNumber": msisdn,
                "trid": trid,
                "name": "Client CashOut",
                "email": "client@test.com",
                "address": "Douala",
                "tag": f"wallet-{wallet_id}",
                "cdata": str({"amount": amount, "wallet_id": wallet_id}),
            },
        )

        logger.info(f"[Cashout] Collect response raw: {collect_resp}")

        # 🔹 Récupération du paymentId si présent
        payment_id = collect_resp.get("paymentId") or collect_resp.get("payment", {}).get("paymentId") or pay_item.get("payItemId")

        # 🔹 Construction du JSON unifié
        unified_response = {
            "wallet_id": wallet_id,
            "amount": amount,
            "channel": channel.upper(),
            "quoteId": quote_id,
            "trid": trid,
            "status": collect_resp.get("status", "PENDING"),
            "ptn": collect_resp.get("ptn"),
            "paymentId": payment_id,
            "reference_proxym": trid,
            "payItem": pay_item,
            "meta": {
                "initiated_at": str(quote_resp.get("created_at", "")),
                "idempotency_key": idempotency_key,
            }
        }

        return unified_response

    # -------------------------------------------------------------------------
   
    @staticmethod
    def verify(trid: str, wallet_id: int = None):
        """
        🔍 Vérifier le statut d’un Cash-Out après confirmation OTP client.
        🔹 Log la réponse brute de l’API externe avant toute transformation
        """
        logger.info(f"[Cashout] Vérification transaction trid={trid}")

        # ⚡ APPEL API externe
        result = MavianceAPIService.verify_transaction(trid)

        # 🔹 LOG de la réponse brute exactement telle qu’elle est reçue
        logger.info(f"[Cashout] Response brute de l'API externe: {result}")

        # Traitement minimal (extraction du premier élément si c'est une liste)
        if isinstance(result, list) and len(result) > 0:
            result = result[0]

        status = result.get("status", "UNKNOWN")
        wallet_credited = False

        # ⚡ Crédit wallet si transaction validée
        if status == "SUCCESS" and wallet_id:
            from wallet.services.wallet_credit_service import WalletCreditService
            try:
                WalletCreditService.credit_wallet(
                    wallet_id=wallet_id,
                    amount=result.get("priceLocalCur"),
                    reference=result.get("trid"),
                    meta=result
                )
                wallet_credited = True
            except Exception as e:
                logger.error(f"[Cashout] Erreur crédit wallet: {e}")

        # 🔹 Construction JSON unifié
        unified_json = {
            "success": True,
            "message": f"🧾 Statut du Cash-Out vérifié avec succès ({status})",
            "status": status,
            "wallet_credited": wallet_credited,
            "ptn": result.get("ptn"),
            "paymentId": result.get("ptn"),
            "trid": result.get("trid"),
            "amount": result.get("priceLocalCur"),
            "timestamp": result.get("timestamp"),
            "raw_response": result  # pour debug / audit
        }

        return unified_json