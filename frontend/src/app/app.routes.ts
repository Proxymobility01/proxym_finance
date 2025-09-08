import { Routes } from '@angular/router';
import {MainLayout} from './layouts/main-layout/main-layout';
import {ContratChauffeurList} from './pages/contrat-chauffeur-list/contrat-chauffeur-list';
import {GarantList} from './pages/garant-list/garant-list';
import {ContratBatterieList} from './pages/contrat-batterie-list/contrat-batterie-list';
import {ChauffeurList} from './pages/chauffeur-list/chauffeur-list';


export const routes: Routes = [

  {
    path: '',
    component: MainLayout,
    children: [

      {
        path: 'contrat/chauffeur',
        component: ContratChauffeurList
      },
      {
        path: 'garants',
        component: GarantList
      },
      {
        path: 'contrat/batterie',
        component: ContratBatterieList
      },
      {
        path: 'chauffeurs',
        component: ChauffeurList
      }
    ]
  }


];
