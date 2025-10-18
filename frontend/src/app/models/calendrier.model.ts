export interface ContratInfo {
  id: number;
  nom_chauffeur: string;
  prenom_chauffeur: string;
  user_unique_id: string;
}


export interface ChauffeurCalendrierItem {
  contrat: ContratInfo;
  paiements: string[]; // ["YYYY-MM-DD", ...]
  paiements_par_jour: Record<string, number>;
  conges: string[]; // ["YYYY-MM-DD", ...]
  resume: {
    total_jours: number;
    jours_payes: number;
    jours_conges: number;
    total_paiements?: number;
  };
}


export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
