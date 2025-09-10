import { Routes } from '@angular/router';
import {MainLayout} from './layouts/main-layout/main-layout';
import {ContratChauffeurList} from './pages/contrat-chauffeur-list/contrat-chauffeur-list';

import {ContratBatterieList} from './pages/contrat-batterie-list/contrat-batterie-list';
import {ChauffeurList} from './pages/chauffeur-list/chauffeur-list';
import {GarantList} from './pages/garant-list/garant-list';
import {Login} from './pages/login/login';
import {CongeList} from './pages/conge-list/conge-list';


export const routes: Routes = [
  {path: 'login', component: Login},




  {
    path: '',
    component: MainLayout,
    children: [

      {
        path: 'garants',
        component: GarantList
      },
      {
        path: 'contrat/chauffeur',
        component: ContratChauffeurList
      },
      {
        path: 'contrat/batterie',
        component: ContratBatterieList
      },
      {
        path: 'chauffeurs',
        component: ChauffeurList
      },
      {
        path:'conges',
        component: CongeList
      }
    ]
  }


];
