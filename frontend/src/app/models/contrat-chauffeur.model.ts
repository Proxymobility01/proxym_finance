
export interface ContratChauffeur{
  id: number;
  reference_contrat: string;
  chauffeur: string
  garant: string;
  reference_contrat_batt:string;
  date_signature: string;
  montant_total: number;
  montant_restant: number;
  montant_paye: number;
  statut: string;
}

export interface ContratChauffeurPayload{
  id: number;
  association_user_moto_id:number;
  garant_id: number;
  contrat_batt_id: number;
  montant_total: string;
  montant_engage:string;
  montant_par_paiement:string;
  date_signature: string;
  date_debut:string;
  duree_jour: number;
  jour_conge_total:number;
  contrat_physique_chauffeur: string;
  contrat_physique_moto_garant: string;
  contrat_physique_batt_garant: string;
}

export interface AssociationUserMoto{
  association_id: number;
  validated_user_id: number;
  moto_validate_id: number;
  nom:string;
  prenom:string;
  vin:string;
}


export const CONTRACT_VALIDATION = {
  POSITIVE_INT_PATTERN: /^\d+$/,
  MONEY_STRING_PATTERN: /^\d{1,3}(\s?\d{3})*(\.\d{1,2})?$/,
  DATE_PATTERN: /^\d{4}-\d{2}-\d{2}$/,
  MAX_MONEY_LEN: 15,
  MAX_FILE_TOKEN: 150
} as const;


