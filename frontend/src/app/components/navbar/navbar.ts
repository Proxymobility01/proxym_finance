import { Component } from '@angular/core';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css'
})
export class Navbar {

  // État des dropdowns
  isContratsDropdownOpen = false;
  isPaiementsDropdownOpen = false;
  isStationsDropdownOpen = false;
  isProfileDropdownOpen = false;
  isSearchVisible = false;

  // Données fictives pour les notifications
  notifications = [
    { id: 1, message: 'Nouveau contrat chauffeur en attente', time: '5 min', type: 'info' },
    { id: 2, message: 'Paiement reçu - Station A', time: '1h', type: 'success' },
    { id: 3, message: 'Maintenance programmée - Station B', time: '2h', type: 'warning' }
  ];

  notificationCount = this.notifications.length;

  constructor() { }

  // Méthodes pour gérer les dropdowns
  toggleContratsDropdown() {
    this.isContratsDropdownOpen = !this.isContratsDropdownOpen;
    this.closOtherDropdowns('contrats');
  }

  togglePaiementsDropdown() {
    this.isPaiementsDropdownOpen = !this.isPaiementsDropdownOpen;
    this.closOtherDropdowns('paiements');
  }

  toggleStationsDropdown() {
    this.isStationsDropdownOpen = !this.isStationsDropdownOpen;
    this.closOtherDropdowns('stations');
  }

  toggleProfileDropdown() {
    this.isProfileDropdownOpen = !this.isProfileDropdownOpen;
    this.closOtherDropdowns('profile');
  }

  toggleSearch() {
    this.isSearchVisible = !this.isSearchVisible;
  }

  closOtherDropdowns(except: string) {
    if (except !== 'contrats') this.isContratsDropdownOpen = false;
    if (except !== 'paiements') this.isPaiementsDropdownOpen = false;
    if (except !== 'stations') this.isStationsDropdownOpen = false;
    if (except !== 'profile') this.isProfileDropdownOpen = false;
  }

  closeAllDropdowns() {
    this.isContratsDropdownOpen = false;
    this.isPaiementsDropdownOpen = false;
    this.isStationsDropdownOpen = false;
    this.isProfileDropdownOpen = false;
    this.isSearchVisible = false;
  }

  // Méthodes de navigation
  navigateToTableauBord() {
    console.log('Navigation vers Tableau de bord');
  }

  navigateToInvestisseurs() {
    console.log('Navigation vers Investisseurs');
  }

  // Méthodes pour les actions du menu Contrats
  navigateToContratsChauf() {
    console.log('Navigation vers Contrats Chauffeurs');
    this.closeAllDropdowns();
  }

  navigateToContratsPartenaires() {
    console.log('Navigation vers Contrats Partenaires');
    this.closeAllDropdowns();
  }

  navigateToContratBatteries() {
    console.log('Navigation vers Contrat Batteries');
    this.closeAllDropdowns();
  }

  navigateToChauffeurs() {
    console.log('Navigation vers Chauffeurs');
    this.closeAllDropdowns();
  }

  navigateToGarants() {
    console.log('Navigation vers Garants');
    this.closeAllDropdowns();
  }

  navigateToPartenaires() {
    console.log('Navigation vers Partenaires');
    this.closeAllDropdowns();
  }

  navigateToConges() {
    console.log('Navigation vers Congés');
    this.closeAllDropdowns();
  }

  // Méthodes pour les actions du menu Paiements
  navigateToPaiementsContrats() {
    console.log('Navigation vers Paiements Contrats');
    this.closeAllDropdowns();
  }

  navigateToHistoriquePaiements() {
    console.log('Navigation vers Historique Paiements');
    this.closeAllDropdowns();
  }

  navigateToPenalites() {
    console.log('Navigation vers Pénalités');
    this.closeAllDropdowns();
  }

  navigateToSwap() {
    console.log('Navigation vers Swap');
    this.closeAllDropdowns();
  }

  navigateToRapports() {
    console.log('Navigation vers Rapports');
    this.closeAllDropdowns();
  }

  // Méthodes pour les actions du menu Stations
  navigateToListeStations() {
    console.log('Navigation vers Liste des stations');
    this.closeAllDropdowns();
  }

  navigateToGestionCharges() {
    console.log('Navigation vers Gestion des charges');
    this.closeAllDropdowns();
  }

  navigateToRentabiliteStations() {
    console.log('Navigation vers Rentabilité de Stations');
    this.closeAllDropdowns();
  }

  // Méthodes pour les actions du menu Profil
  navigateToProfile() {
    console.log('Navigation vers Mon profil');
    this.closeAllDropdowns();
  }

  navigateToParametres() {
    console.log('Navigation vers Paramètres');
    this.closeAllDropdowns();
  }

  logout() {
    console.log('Déconnexion');
    this.closeAllDropdowns();
    // Logique de déconnexion ici
  }

  // Méthode de recherche
  onSearch(event: any) {
    const searchTerm = event.target.value;
    console.log('Recherche:', searchTerm);
    // Logique de recherche ici
  }

  markNotificationAsRead(notificationId: number) {
    this.notifications = this.notifications.filter(n => n.id !== notificationId);
    this.notificationCount = this.notifications.length;
  }

}
