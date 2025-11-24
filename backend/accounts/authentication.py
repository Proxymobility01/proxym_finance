import requests
from django.core.cache import cache
from jose import jwt
from jose.exceptions import JOSEError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import CustomUser


def get_jwks():
    """
    Récupère le JWKS, en utilisant le cache de Django avec un TTL.
    """
    cache_key = "AUTH_SERVICE_JWKS"  # Clé unique pour le cache

    # 3. Essayer de récupérer du cache de Django
    jwks = cache.get(cache_key)

    if jwks:
        return jwks  # Trouvé dans le cache

    # 4. Si non trouvé, le télécharger
    try:
        response = requests.get(settings.AUTH_JWKS_URL)
        response.raise_for_status()
        jwks = response.json()

        # 5. Le mettre en cache pour une durée définie (ex: 24 heures)
        # timeout est en secondes (60 sec * 60 min * 24 heures)
        cache.set(cache_key, jwks, timeout=60 * 60 * 24)

        return jwks
    except Exception as e:
        # Si le téléchargement échoue, on ne peut pas valider les tokens
        raise AuthenticationFailed(f"Impossible de récupérer le JWKS depuis l'IdP: {e}")

class OIDCAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            # 1. Obtenir la clé publique depuis le JWKS
            jwks = get_jwks()
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            public_key = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
            if not public_key:
                raise AuthenticationFailed("Clé publique (kid) non trouvée dans le JWKS.")

            # 2. Décoder et valider le token (signature, expiration, issuer)
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.AUTH_ISSUER,
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expiré.")
        except (JOSEError, Exception) as e:
            raise AuthenticationFailed(f"Token invalide: {e}")

        # 3. LE SUCCÈS : Trouver l'utilisateur local
        user = self.get_local_user(claims)
        if not user or not user.is_active:
            raise AuthenticationFailed("Utilisateur authentifié mais inconnu ou inactif dans l'application Finance.")

        return (user, token) # Succès!

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