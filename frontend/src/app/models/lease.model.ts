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

export interface Lease{
  id: number;
  chauffeur_unique_id: string;
  chauffeur: string;
  moto_unique_id: string;
  moto_vin:string;
  montant_moto: string;
  montant_batterie: string;
  date_concernee: string;
  date_limite: string;
  methode_paiement: string;
  station_paiement: string;
  statut_paiement: string;
  statut_penalite:string;
  paye_par:string;
  created:string;
}

export interface LeaseApiResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: any[];
}
