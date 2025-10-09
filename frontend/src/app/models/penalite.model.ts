export interface Penalite {
  id: number;
  reference_contrat: string;
  chauffeur: string;
  montant_penalite: string;
  type_penalite: string;
  motif_penalite: string;
  echeance_paiement_penalite:string;
  description:string;
  statut_penalite:string;
  date_paiement_manquee:string;
  montant_paye:string;
  montant_restant:string;
  created:string;
  annulee_par_label:string;
  justificatif_annulation:string;
  date_annulation:string;
}

export type StatutPenalite = 'non_paye' | 'partiellement_paye' | 'paye';
export type TypePenalite = 'legere' | 'grave';
export interface PaiementPenalitePayload{
  penalite_id:number;
  "montant":number | string;
  "methode_paiement":string;
  reference_transaction?:string | null;
}
