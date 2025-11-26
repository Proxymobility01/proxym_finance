"""
# wallet/services/deposit_service.py
import logging
from contextlib import contextmanager
from wallet.models import Wallet, Transaction
from wallet.services.maviance_api_service import MavianceAPIService
import requests

logger = logging.getLogger("wallet")


class DepositService:
    
   # Service de dépôt (Cash-in) connecté à Smobilpay.
   # Gestion automatique de la création du quote, de la collecte et du suivi.
   

    PAY_ITEM_IDS = {
        "mtn": "S-112-948-MTNMOMO-20052-200040001-1",            # ✅ MTN MOMO
        "orange": "S-112-948-CMORANGEOM-30052-2006125104-1",     # ✅ ORANGE MONEY
    }

    @classmethod
    def get_pay_item_id(cls, channel: str) -> str:
     #   Retourne le PayItemId correspondant au canal choisi."
        return cls.PAY_ITEM_IDS.get(channel.lower())

    # ===============================================================
    # ⚙️ Contexte transactionnel
    # ===============================================================
    @classmethod
    @contextmanager
    def _ctx(cls, wallet, amount):
        logger.info("[Deposit] INIT START")
        t = Transaction.objects.create(
            wallet=wallet,
            montant=amount,
            type="depot",
            statut="INITIATED"
        )
        try:
            yield t
        except Exception as e:
            logger.error(f"[Deposit] INIT FAILED: {e}")
            t.statut = "FAILED"
            t.save(update_fields=["statut"])
            raise
        else:
            t.statut = "SUCCESS"
            t.save(update_fields=["statut"])

    # ===============================================================
    # 🚀 Lancement complet du flux de dépôt (quote + collect)
    # ===============================================================
    @classmethod
    def initiate(cls, wallet_id, amount, channel, msisdn, idempotency_key, **kwargs):
        wallet = Wallet.objects.get(pk=wallet_id)
        logger.info(f"[DepositInit] Start wallet={wallet_id}, data={{'amount': '{amount}', 'channel': '{channel}', 'msisdn': '{msisdn}'}}")

        pay_item_id = cls.get_pay_item_id(channel)
        if not pay_item_id:
            raise ValueError(f"❌ Canal de paiement '{channel}' non reconnu. Choisissez 'mtn' ou 'orange'.")

        if float(amount) < 100:
            raise ValueError("❌ Le montant minimum autorisé par Smobilpay est de 100 XAF.")

        msisdn_last9 = msisdn[-9:]  # Smobilpay accepte le format sans indicatif pays

        with cls._ctx(wallet, amount) as tx:
            logger.info(f"[Deposit] TX created id={tx.id}")
            logger.info(f"[Deposit] Canal={channel.upper()} PayItem={pay_item_id} MSISDN={msisdn}")

            try:
                # 1️⃣ Quote
                quote_resp = MavianceAPIService.create_quote(pay_item_id, float(amount))
                quote_id = quote_resp.get("quoteId")
                logger.info(f"[Deposit] Quote={quote_id}")

                # 2️⃣ Collect
                customer_info = {
                    "phone": msisdn_last9,
                    "email": "client@test.com",
                    "name": "Client Test",
                    "address": "MambandaBonaberi",
                    "serviceNumber": msisdn_last9,
                    "trid": str(tx.id),
                }

                collect_payload = {
                    **customer_info,
                    "quoteId": quote_id,
                    "tag": f"wallet-{wallet.id}",
                    "cdata": str({"amount": float(amount), "wallet_id": wallet.id}),
                }

                collect_resp = MavianceAPIService.collect_payment(quote_id, collect_payload)
                logger.info(f"[Deposit] Collect resp: {collect_resp}")

            except requests.exceptions.HTTPError as e:
                # 📡 Gestion propre des erreurs Smobilpay
                resp = getattr(e.response, "json", lambda: {})()
                logger.error(f"[S3P] Error: {e} -> {resp}")

                customer_msg = None
                if isinstance(resp, dict):
                    msgs = resp.get("customerMsg")
                    if isinstance(msgs, list) and len(msgs) > 0:
                        # On récupère le message en français si dispo
                        customer_msg = next(
                            (m["content"] for m in msgs if m.get("language") == "fr"),
                            msgs[0].get("content", None)
                        )

                error_msg = customer_msg or "Échec de la transaction sur Smobilpay."
                raise ValueError(f"⚠️ {error_msg}")

            # ✅ Enregistrement transaction
            tx.s3p_quote_id = quote_id
            tx.reference_proxym = collect_resp.get("trid", str(tx.id))
            tx.s3p_trid = collect_resp.get("trid")
            tx.statut = collect_resp.get("status", "PENDING")
            tx.save()

            result = {
                **collect_resp,
                "wallet_id": wallet.id,
                "reference_proxym": tx.reference_proxym,
                "quoteId": quote_id,
            }
            logger.info(f"[DepositInit] Result: {result}")
            return result

    # ===============================================================
    # 🔍 Vérification finale du statut de transaction
    # ===============================================================
    @classmethod
    def finalize(cls, trid=None, reference_proxym=None):
        if not trid and not reference_proxym:
            raise ValueError("❌ Fournir 'trid' ou 'reference_proxym'.")

        verify_resp = MavianceAPIService._request("GET", f"/verifytx?trid={trid}")
        logger.info(f"[DepositVerify] Response: {verify_resp}")

        tx = Transaction.objects.filter(s3p_trid=trid).first()
        if tx:
            tx.statut = verify_resp.get("status", tx.statut)
            tx.save(update_fields=["statut"])

        result = {
            "wallet_id": tx.wallet.id if tx else None,
            "status": verify_resp.get("status", "UNKNOWN"),
            "new_balance": tx.wallet.solde if tx and hasattr(tx.wallet, "solde") else None,
            "trid": trid,
        }
        return result
"""