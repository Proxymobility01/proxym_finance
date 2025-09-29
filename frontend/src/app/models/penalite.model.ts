export interface Penalite {
  id: number;
  reference_contrat: string;
  chauffeur: string;
  montant_penalite: string;
  type_penalite: string;
  motif_penalite: string;
  description:string;
  statut_penalite:string;
  date_paiement_manquee:string;
  montant_paye:string;
  montant_restant:string;
}

export type StatutPenalite = 'non_paye' | 'partiellement_paye' | 'paye';
export interface PaiementPenalitePayload{
  penalite_id:number;
  "montant":number | string;
  "methode_paiement":string;
  reference_transaction?:string | null;
}
