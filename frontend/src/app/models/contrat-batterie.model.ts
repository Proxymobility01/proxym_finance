export interface ContratBatteriesPayload{
  id: number;
  montant_total: number;
  montant_engage: number;
  montant_caution: number;
  date_signature: string;
  date_debut: string;
  duree_jour:string;
  date_fin:string;
  contrat_physique_batt:string[];
}


export interface ContratBatterie{
  id: number;
  reference_contrat:string;
  montant_total: number;
  montant_paye: number;
  montant_restant: number;
  date_signature: string;
  date_debut: string;
  date_fin: string;
  duree_jour:string;
  statut:string;
  montant_engage:string;
  montant_caution:string;
  contrat_physique_batt:string;
  proprietaire:string;
}
