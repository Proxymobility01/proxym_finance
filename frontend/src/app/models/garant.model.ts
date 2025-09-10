export interface GarantPayload {
  id: number;
  nom: string | null;
  prenom: string | null;
  tel: string | null;
  ville: string | null;
  quartier: string | null;
  photo: string | null;
  plan_localisation: string | null;
  cni_recto: string | null;
  cni_verso: string | null;
  justif_activite: string | null;
  profession: string | null;
}

export type Mode = 'create' | 'edit';

export interface GarantDialogData {
  mode: Mode;
  id?: number;
  garant?: Partial<Garant>;
}

export interface Garant{
  id: number;
  nom: string;
  prenom: string | null;
  tel: string | null;
  ville: string | null;
  quartier: string | null;
  profession: string | null;

  // chemins relatifs (stockés en base)
  photo: string | null;
  plan_localisation: string | null;
  cni_recto: string | null;
  cni_verso: string | null;
  justif_activite: string | null;
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



