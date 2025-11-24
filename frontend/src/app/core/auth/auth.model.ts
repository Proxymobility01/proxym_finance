/**
 * Profil Local (de l'API Finance)
 * Reçu de l'endpoint /me/ de la finance. C'est ce que l'UI utilise.
 * Basé sur votre JSON.
 */
export interface LocalProfile {
  id: number; // ID local de la finance
  email: string;
  nom: string;
  prenom: string;
  tel: string;
  role: {
    nomRole: string;
  } | null;
}

/**
 * Profil central (de l'IdP)
 * Reçu lors du login (partie "profile" de la réponse).
 */
export interface CentralProfile {
  id: number;
  email: string | null;
  username: string | null;
  phone: string | null;
  tel: string | null;
  user_agence_unique_id: string | null;
  agence_unique_id: string | null;
  users_entrepot_unique_id: string | null;
  app_type: string | null;
}

/**
 * Réponse de l'endpoint POST /auth/token/ (de l'IdP)
 */
export interface AuthResponse {
  access: string;
  profile: CentralProfile;
}

/**
 * Réponse de l'endpoint POST /auth/token/refresh/ (de l'IdP)
 */
export interface RefreshResponse {
  access: string;
}
