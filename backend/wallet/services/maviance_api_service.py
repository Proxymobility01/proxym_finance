import requests
import logging
from wallet.services.s3p_auth_service import S3PAuthService

logger = logging.getLogger("wallet")


class MavianceAPIService:
    """
    Client sécurisé pour Smobilpay S3P v3.0.5
    Gère : GET signés / POST signés / JSON parsing
    """

    BASE_URL = "https://s3p.smobilpay.staging.maviance.info/v2"

    @classmethod
    def _request(cls, method: str, path: str, payload: dict | None = None):
        url = f"{cls.BASE_URL}{path}"
        headers = S3PAuthService.build_headers(method, url, payload)

        logger.info(f"[S3P] {method.upper()} {url} PAYLOAD={payload}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=payload, timeout=30)
            else:
                response = requests.post(url, headers=headers, data=payload, timeout=30)

            response.raise_for_status()
            json_resp = response.json()

            logger.info(f"[S3P] Response {response.status_code}: {json_resp}")
            return json_resp

        except Exception as e:
            try:
                logger.error(f"[S3P] ERROR {e} : {response.text}")
            except:
                logger.error(f"[S3P] ERROR {e}")
            raise

    # -------------------------------------------------------------
    # 1️⃣ QUOTE
    # -------------------------------------------------------------
    @classmethod
    def create_quote(cls, pay_item_id: str, amount: float):
        payload = {
            "payItemId": pay_item_id,
            "amount": amount
        }
        return cls._request("POST", "/quotestd", payload)

    # -------------------------------------------------------------
    # 2️⃣ COLLECT
    # -------------------------------------------------------------
    @classmethod
    def collect_payment(cls, quote_id: str, customer: dict):
        payload = {
            "quoteId": quote_id,
            "customerPhonenumber": customer["phone"],
            "customerEmailaddress": customer.get("email", "client@test.com"),
            "customerName": customer.get("name", "Client Proxym"),
            "customerAddress": customer.get("address", "Douala"),
            "serviceNumber": customer.get("serviceNumber", customer["phone"]),
            "trid": customer.get("trid"),
            "tag": customer.get("tag", "proxym-wallet"),
            "cdata": customer.get("cdata", "{}"),
        }
        return cls._request("POST", "/collectstd", payload)

    # -------------------------------------------------------------
    # 3️⃣ VERIFY
    # -------------------------------------------------------------
    @classmethod
    def verify_transaction(cls, trid: str):
        payload = {"trid": trid}
        return cls._request("GET", "/verifytx", payload)
