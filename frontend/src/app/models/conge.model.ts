export interface CongePayload{
  id: number;
  contrat_id: number;
  date_debut: string;
  date_fin: string;
  motif: string;
}

export interface Conge{
  id: number;
  titulaire_contrat: string;
  reference_contrat:string;
  statut: string;
  date_debut: string;
  date_fin: string;
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
