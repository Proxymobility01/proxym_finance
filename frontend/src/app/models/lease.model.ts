export interface PaiementLeasePayload {
  id: number;
  contrat_id: number;
  methode_paiement: string;
  date_paiement_concerne: string;
  date_limite_paiement: string;
  montant_moto: string;
  montant_batt: string;
  reference_transaction: string;
}

export interface LeaseFilters {
  q?: string;
  statut?: '' | 'PAYE' | 'NON_PAYE';
  paye_par?: string;
  station?: string;
  date_concernee?: string;
  date_concernee_after?: string;
  date_concernee_before?: string;
  created?: string;
  created_after?: string;
  created_before?: string;
}

export interface CombinedExportFilters extends LeaseFilters {
  q?: string;
  statut?: 'PAYE' | 'NON_PAYE' | '';
  paye_par?: string;
  station?: string;
}

export interface Lease{
  id: number;
  chauffeur_unique_id: string;
  chauffeur: string;
  moto_unique_id: string;
  moto_vin:string;
  montant_moto: string;
  montant_batterie: string;
  montant_total:number;
  date_concernee: string;
  date_limite: string;
  methode_paiement: string | null;
  station_paiement: string;
  statut_paiement: string;
  statut_penalite:string;
  paye_par:string;
  created:string;
  source?: 'PAYE' | 'NON_PAYE';
}


