import base64
import hashlib
import hmac
import time
import urllib.parse
from django.conf import settings


class S3PAuthService:
    """
    🔐 Générateur sécurisé d’en-têtes d’authentification S3P (Smobilpay)
    Conforme à la doc officielle v3.0.5 (HMAC-SHA1 + x-www-form-urlencoded)
    """

    S3P_PUBLIC_KEY = getattr(settings, "S3P_PUBLIC_KEY", "99852b63-4b50-4712-b905-f8251172a191")
    S3P_SECRET = getattr(settings, "S3P_SECRET", "abfe7106-58e3-4069-86ec-db076dbed629")

    @classmethod
    def build_headers(cls, method: str, full_url: str, params: dict | None = None) -> dict:
        """
        Construit le header d’authentification complet.
        - Signature conforme à Smobilpay
        - Support GET (params dans query) et POST (params dans body)
        """
        ts = str(int(time.time()))
        nonce = str(int(time.time() * 1_000_000))

        # Fusionner paramètres applicatifs + auth
        base_params = (params or {}) | {
            "s3pAuth_nonce": nonce,
            "s3pAuth_signature_method": "HMAC-SHA1",
            "s3pAuth_timestamp": ts,
            "s3pAuth_token": cls.S3P_PUBLIC_KEY,
        }

        # Étape 1 : tri alphabétique
        sorted_param_str = "&".join(f"{k}={base_params[k]}" for k in sorted(base_params.keys()))

        # Étape 2 : construction du base string
        encoded_url = urllib.parse.quote(full_url, safe="")
        encoded_params = urllib.parse.quote(sorted_param_str, safe="")
        base_string = f"{method.upper()}&{encoded_url}&{encoded_params}"

        # Étape 3 : calcul HMAC-SHA1 + encodage Base64
        signature = base64.b64encode(
            hmac.new(cls.S3P_SECRET.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()

        # Étape 4 : assemblage de l’Authorization Header
        auth_header = (
            's3pAuth, '
            f's3pAuth_nonce="{nonce}", '
            f's3pAuth_signature="{signature}", '
            's3pAuth_signature_method="HMAC-SHA1", '
            f's3pAuth_timestamp="{ts}", '
            f's3pAuth_token="{cls.S3P_PUBLIC_KEY}"'
        )

        return {
            "Authorization": auth_header,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
