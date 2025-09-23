// src/app/models/conge.model.ts

export type CongeStatut = 'en_attente' | 'approuve' | 'rejete' | 'annule' | 'termine';

export interface CongeCreatePayload {
  contrat_id: number;
  contrat_id_read?: number;
  date_debut: string;
  date_fin: string;
  date_reprise: string;
  nb_jour: number;
  motif_conge: string;
}

export interface CongeUpdatePayload extends Partial<Omit<CongeCreatePayload, 'contrat_id'>> {
  // on peut autoriser la mise à jour d'autres champs si besoin.
  statut: CongeStatut; // 👈 requis en update
}

export interface CongePayload extends CongeCreatePayload {
  id: number;
  statut: CongeStatut; // lecture “complète“ d’un congé
}

export interface Conge {
  id: number;
  contrat_id_read: number;
  chauffeur: string;
  reference_contrat: string;
  statut: CongeStatut;
  date_debut: string;
  date_fin: string;
  date_reprise: string;
  nb_jour: number;
  motif_conge: string;

}

export const MOTIF_SAFE_REGEX =
  /^[\p{L}\p{N}\s.,;:!?'()"_\-\/&@%+*#€$£°]+$/u;

export type Mode = 'create' | 'edit';

export interface CongeDialogData {
  mode: Mode;
  id?: number;
  // on rend tout optionnel pour pré-remplir facilement en edit
  conge?: Partial<CongePayload & { reference_contrat?: string }>;
}
