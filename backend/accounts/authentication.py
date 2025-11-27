import requests
from django.core.cache import cache
from jose import jwt
from jose.exceptions import JOSEError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import CustomUser


def get_jwks(force_refresh=False):
    """
    Récupère le JWKS. Si force_refresh=True, on ignore le cache et on retélécharge.
    """
    cache_key = "AUTH_SERVICE_JWKS"

    # 1. Si on ne force pas le refresh, on tente le cache
    if not force_refresh:
        jwks = cache.get(cache_key)
        if jwks:
            return jwks

    # 2. Sinon (ou si cache vide), on télécharge
    try:
        # print("🔄 Téléchargement des clés JWKS...") # Debug
        response = requests.get(settings.AUTH_JWKS_URL, timeout=5)
        response.raise_for_status()
        jwks = response.json()

        # 3. On met en cache
        cache.set(cache_key, jwks, timeout=60 * 60 * 24)

        return jwks
    except Exception as e:
        raise AuthenticationFailed(f"Impossible de récupérer le JWKS: {e}")

class OIDCAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            # 1. Lire le header du token SANS le vérifier (pour avoir le KID)
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid:
                raise AuthenticationFailed("Token invalide: 'kid' manquant dans le header.")

            # 2. Récupérer les clés en cache
            jwks = get_jwks(force_refresh=False)

            # 3. Chercher la clé correspondante
            public_key = self.find_key_in_jwks(jwks, kid)

            # 🚨 SCÉNARIO ROTATION DE CLÉ 🚨
            # Si on ne trouve pas la clé, c'est peut-être une rotation récente.
            # On force le re-téléchargement du JWKS.
            if not public_key:
                # print(f"⚠️ Clé {kid} introuvable dans le cache. Tentative de refresh...")
                jwks = get_jwks(force_refresh=True)
                public_key = self.find_key_in_jwks(jwks, kid)

            # Si après refresh on ne trouve toujours pas, c'est vraiment un faux token
            if not public_key:
                raise AuthenticationFailed("Clé publique introuvable (Rotation ou Token falsifié).")

            # 4. Décoder et valider le token avec la bonne clé
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.AUTH_ISSUER,
                # audience=... (si tu gères l'audience)
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expiré.")
        except (JOSEError, Exception) as e:
            raise AuthenticationFailed(f"Token invalide: {e}")

        # 5. Provisioning / Récupération User (inchangé)
        user = self.get_local_user(claims)
        if not user or not user.is_active:
            raise AuthenticationFailed("Utilisateur inconnu ou inactif.")

        return (user, token)

    def find_key_in_jwks(self, jwks, kid):
        """Helper pour trouver une clé par son kid"""
        return next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)

    def get_local_user(self, claims):
        """
        Trouve l'utilisateur dans la BDD locale de la Finance
        en utilisant le "pont" auth_user_id_central.
        """
        auth_user_id = claims.get("auth_user_id")
        if not auth_user_id:
            return None

        try:
            # C'est ici que le lien se fait !
            return CustomUser.objects.get(auth_user_id_central=auth_user_id)
        except CustomUser.DoesNotExist:
            return None