
export interface Contrat{
  id: number;
  reference: string;
  nom_chauffeur: string
  date_signature: string;
  montant_total: number;
  montant_restant: number;
  montant_paye: number;
  status: boolean;
}

export type Filters = {
  q?: string | null;                 // recherche globale json-server
  status?: boolean | null;           // filtre exact (true/false)
  // tu peux ajouter d'autres filtres exacts: reference, nom_chauffeur, etc.
};

export type Order = 'asc' | 'desc';
export type Pagination = { page?: number; page_size?: number };
export type Sorting = { sort?: keyof Contrat | ''; order?: Order };
