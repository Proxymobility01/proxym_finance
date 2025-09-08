export interface GarantPayload {
  id: number;
  nom: string;
  prenom: string;
  tel: string;
  ville: string;
  quartier: string;
  photo: string[];
  plan_localisation:string[];
  cni_recto:string[];
  cni_verso:string[];
  justif_activite:string[];
  profession:string;
}

export interface Garant{
  id: number;
  nom: string;
  prenom: string;
  tel: string;
  ville: string;
  quartier: string;
  profession: string;
}

export const VALIDATION = {
  // autorise lettres accentuées (unicode), chiffres, espace, apostrophe (simples et typographiques),
  // tiret, point, virgule. Interdit & @ _ etc.
  SAFE_TEXT_PATTERN: /^[\p{L}\p{M}\p{N} '\-.,]+$/u,

  // uniquement des chiffres (pas de contrainte de longueur ici, tu peux en ajouter si tu veux)
  TELEPHONE_PATTERN: /^\d+$/,

  MIN_TEXT: 3,
  MAX_TEXT: 30
} as const;



