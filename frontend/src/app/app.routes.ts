import { Routes } from '@angular/router';
import { MainLayout } from './layouts/main-layout/main-layout';
import { ContratChauffeurList } from './pages/contrat-chauffeur-list/contrat-chauffeur-list';
import { ContratBatterieList } from './pages/contrat-batterie-list/contrat-batterie-list';
import { GarantList } from './pages/garant-list/garant-list';
import { Login } from './pages/login/login';
import { CongeList } from './pages/conge-list/conge-list';
import { LeaseList } from './pages/lease-list/lease-list';
import { PenaliteList } from './pages/penalite-list/penalite-list';
import {authGuard} from './core/auth/auth-guard';
import {NotFound} from './pages/not-found/not-found';
import {Calendrier} from './pages/calendrier/calendrier';


export const routes: Routes = [
  { path: 'login', component: Login },

  {
    path: '',
    component: MainLayout,
    canActivate: [authGuard], // 🔐 protège tout MainLayout
    data: { role: 'GestionnaireFinancier' }, // rôle exigé
    children: [
      { path: 'garants', component: GarantList },
      { path: 'contrat/chauffeur', component: ContratChauffeurList },
      { path: 'contrat/batterie', component: ContratBatterieList },
      { path: 'conges', component: CongeList },
      { path: 'paiements/contrats', component: LeaseList },
      { path: 'paiements/penalites', component: PenaliteList },
      {path: 'calendrier', component: Calendrier}
    ],
  },


  { path: '**', component: NotFound },
];
