export interface LoginResponse {
    refresh: string;
    access: string;
    id:number;
    email:string;
    nom:string;
    prenom:string;
    role:string;
}


export const STORAGE_KEYS = {
  access: 'access_token',
  refresh: 'refresh_token',
  userId: 'user_id',
  nom: 'user_nom',
  prenom: 'user_prenom',
  role: 'role',
} as const;
