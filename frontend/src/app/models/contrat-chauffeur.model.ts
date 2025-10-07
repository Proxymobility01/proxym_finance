
export interface ContratChauffeur{
  id: number;
  reference_contrat: string;
  chauffeur: string
  association_user_moto_id:number;
  date_debut:string;
  garant: string;
  garant_id?: number;
  contrat_batt:number;
  reference_contrat_batt:string;
  montant_engage: string;
  montant_par_paiement: string;
  montant_par_paiement_batt: string;
  montant_engage_batt: string;
  date_signature: string;
  montant_total: number;
  montant_restant: number;
  montant_paye: number;
  statut: string;
  date_concernee: string;
  date_limite: string;
  jour_conge_total: number;
  jour_conge_utilise:number;
  jour_conge_restant:number;
  contrat_physique_chauffeur:string;
  contrat_physique_moto_garant:string;
  contrat_physique_batt_garant:string;
}


export interface AssociationUserMoto{
  association_id: number;
  validated_user_id: number;
  moto_validate_id: number;
  nom:string;
  prenom:string;
  vin:string;
}

export type Mode = 'create' | 'edit';

export interface ContratChauffeurDialogData {
  mode: Mode;
  id?: number;
  contrat?: Partial<ContratChauffeur>;
}

export type FileKind =
  | 'contrat_physique_chauffeur'
  | 'contrat_physique_moto_garant'
  | 'contrat_physique_batt_garant';

export const CONTRACT_VALIDATION = {
  POSITIVE_INT_PATTERN: /^\d+$/,
  MONEY_STRING_PATTERN: /^\d{1,3}(\s?\d{3})*(\.\d{1,2})?$/,
  DATE_PATTERN: /^\d{4}-\d{2}-\d{2}$/,
  MAX_MONEY_LEN: 15,
  MAX_FILE_TOKEN: 150
} as const;


