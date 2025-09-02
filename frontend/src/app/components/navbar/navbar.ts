


import { Component, HostListener, inject, signal, computed, OnInit } from '@angular/core';
import {Router, NavigationEnd, RouterLink, RouterLinkActive} from '@angular/router';

type DropKey = 'contrats' | 'paiements' | 'stations' | 'profile' | null;

interface Notification {
  id: number;
  message: string;
  time: string;
  type: 'info' | 'success' | 'warning';
}

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.html',
  imports: [
    RouterLink,
    RouterLinkActive,
  ],
  styleUrls: ['./navbar.css']
})
export class Navbar implements OnInit {

  private readonly router = inject(Router);

  // État unifié pour TOUS les dropdowns
  readonly openKey = signal<DropKey>(null);
  readonly searchVisible = signal<boolean>(false);

  // Notifications (exemple)
  readonly notificationsSig = signal<Notification[]>([
    { id: 1, message: 'Nouveau contrat chauffeur en attente', time: '5 min', type: 'info' },
    { id: 2, message: 'Paiement reçu - Station A', time: '1h', type: 'success' },
    { id: 3, message: 'Maintenance programmée - Station B', time: '2h', type: 'warning' }
  ]);
  readonly notificationCount = computed(() => this.notificationsSig().length);

  ngOnInit(): void {
    // Fermer tout à chaque navigation
    this.router.events.subscribe(e => {
      if (e instanceof NavigationEnd) this.closeAllDropdowns();
    });
  }

  // Helpers d’ouverture/fermeture
  toggle(key: Exclude<DropKey, null>) {
    this.openKey.update(k => (k === key ? null : key));
  }
  isOpen(key: Exclude<DropKey, null>): boolean {
    return this.openKey() === key;
  }
  closeAllDropdowns() {
    this.openKey.set(null);
    this.searchVisible.set(false);
  }
  toggleSearch() {
    this.searchVisible.update(v => !v);
  }

  // Clic hors navbar -> fermeture
  @HostListener('document:click', ['$event'])
  onDocClick(ev: MouseEvent) {
    const target = ev.target as HTMLElement;
    const navbar = document.querySelector('.custom-navbar');
    if (navbar && !navbar.contains(target)) this.closeAllDropdowns();
  }

  // Notifications
  markNotificationAsRead(notificationId: number) {
    const next = this.notificationsSig().filter(n => n.id !== notificationId);
    this.notificationsSig.set(next);
  }

  // Déconnexion (placeholder)
  logout() {
    // TODO: logique de déconnexion
    this.closeAllDropdowns();
  }



  /**
   * Vérifie si la route actuelle correspond exactement à l'URL donnée
   */
  isCurrentRoute(url: string): boolean {
    return this.router.url === url;
  }

  /**
   * Vérifie si la section Contrats est active
   */
  isContratSectionActive(): boolean {
    const currentUrl = this.router.url;
    const contratRoutes = [
      '/contrat/chauffeur',
      '/contrat/partenaire',
      '/contrat/batterie',
      '/chauffeurs',
      '/garants',
      '/partenaires',
      '/conges'
    ];

    return contratRoutes.some(route => currentUrl.startsWith(route));
  }

  /**
   * Vérifie si la section Paiements est active
   */
  isPaiementSectionActive(): boolean {
    const currentUrl = this.router.url;
    const paiementRoutes = [
      '/paiements/contrats',
      '/paiements/historique',
      '/paiements/penalites',
      '/swap',
      '/rapports'
    ];

    return paiementRoutes.some(route => currentUrl.startsWith(route));
  }

  /**
   * Vérifie si la section Stations est active
   */
  isStationSectionActive(): boolean {
    const currentUrl = this.router.url;
    const stationRoutes = [
      '/stations'
    ];

    return stationRoutes.some(route => currentUrl.startsWith(route));
  }
}
