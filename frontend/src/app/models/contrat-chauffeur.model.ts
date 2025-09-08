
export interface ContratChauffeur{
  id: number;
  reference: string;
  nom_chauffeur: string
  date_signature: string;
  montant_total: number;
  montant_restant: number;
  montant_paye: number;
  status: boolean;
}

export interface ContratChauffeurPayload{
  id: number;
  association_user_moto_id:number;
  garant_id: number;
  contrat_batt_id: number;
  montant_total: string;
  montant_engage:string
  date_signature: string;
  date_debut:string;
  duree_jour: number;
  jour_conge_total:number;
  contrat_physique_chauffeur: string[];
  contrat_physique_moto_garant: string[];
  contrat_physique_batt_garant: string[];
}


export const CONTRACT_VALIDATION = {
  POSITIVE_INT_PATTERN: /^\d+$/,
  MONEY_STRING_PATTERN: /^\d{1,3}(\s?\d{3})*(\.\d{1,2})?$/,
  DATE_PATTERN: /^\d{4}-\d{2}-\d{2}$/,
  MAX_MONEY_LEN: 15,
  MAX_FILE_TOKEN: 150
} as const;


