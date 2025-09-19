export interface CongePayload{
  id: number;
  contrat_id: number;
  date_debut: string;
  date_fin: string;
  date_reprise:string
  nb_jour: number;
  motif_conge: string;
}

export interface Conge{
  id: number;
  chauffeur: string;
  reference_contrat:string;
  statut: string;
  date_debut: string;
  date_fin: string;
  date_reprise:string
  nb_jour: number;
  motif: string;
}

export const MOTIF_SAFE_REGEX =
  /^[\p{L}\p{N}\s.,;:!?'()"_\-\/&@%+*#€$£°]+$/u;

export type Mode = 'create' | 'edit';

export interface CongeDialogData {
  mode: Mode;
  id?: number;
  conge?: Partial<CongePayload & { reference_contrat?: string }>;
}
