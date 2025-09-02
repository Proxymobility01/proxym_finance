import { Routes } from '@angular/router';
import {MainLayout} from './layouts/main-layout/main-layout';
import {ContratChauffeurList} from './pages/contrat-chauffeur-list/contrat-chauffeur-list';


export const routes: Routes = [

  {
    path: '',
    component: MainLayout,
    children: [

      {
        path: 'contrat/chauffeur',
        component: ContratChauffeurList
      }
    ]
  }


];
