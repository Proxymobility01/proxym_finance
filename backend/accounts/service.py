
import requests
from django.conf import settings
def sync_user_with_auth_service(user, raw_password=None):
    """
    Envoie l'utilisateur Finance vers Auth Service.
    Met à jour user.auth_user_id_central avec la réponse.
    """

    # 1. Préparation des données pour AuthUser (Auth Service)
    # On génère un username simple basé sur Prénom + Nom
    generated_username = f"{user.prenom or ''}.{user.nom}".lower().replace(" ", "").strip('.')
    if not generated_username:
        generated_username = user.email.split('@')[0]

    payload = {
        # --- Champs obligatoires / Clés de recherche ---
        "email": user.email,
        "tel": user.tel,

        # --- Identification Cross-App ---
        "app_type": "finance",  # C'est nous !
        "tenant_id": str(user.id),  # L'ID local de Finance

        # --- Infos supplémentaires ---
        "username": generated_username,
        "first_name": user.prenom or "",
        "last_name": user.nom or "",
    }

    # Si on a un mot de passe brut (création), on l'envoie
    if raw_password:
        payload["password"] = raw_password

    headers = {
        "X-Service-Key": settings.SERVICE_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        # 2. Appel API Synchronous
        response = requests.post(
            settings.AUTH_SERVICE_PROVISION_URL,
            json=payload,
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            # 3. Récupération de l'ID Central et Sauvegarde
            remote_id = data.get("auth_user_id")
            if remote_id:
                user.auth_user_id_central = remote_id
                user.save(update_fields=["auth_user_id_central"])
                return True, "Utilisateur synchronisé avec Auth Service."

        return False, f"Erreur Auth Service ({response.status_code}): {response.text}"

    except Exception as e:
        return False, f"Erreur connexion Auth Service: {str(e)}"