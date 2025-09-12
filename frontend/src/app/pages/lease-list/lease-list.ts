// src/app/pages/leases/lease-list.ts
import { Component, OnInit, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LeaseService } from '../../services/lease';
import { Lease } from '../../models/lease.model';

type PageItem = { type: 'page'; index: number } | { type: 'dots' };

@Component({
  selector: 'app-lease-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './lease-list.html',
  styleUrls: ['./lease-list.css'],
})
export class LeaseList implements OnInit {
  private readonly leaseService = inject(LeaseService);

  // ---------- Source ----------
  readonly leases    = this.leaseService.leases;
  readonly isLoading = this.leaseService.isLoadingLeases;
  readonly error     = this.leaseService.errorLeases;

  ngOnInit() {
    this.leaseService.fetchLeases();
  }

  // ---------- Filtres ----------
  readonly query             = signal<string>('');          // recherche multi-champs
  readonly statutPaiement    = signal<string>('');          // liste déroulante
  readonly statutPenalite    = signal<string>('');          // liste déroulante
  readonly payePar           = signal<string>('');          // liste déroulante
  readonly stationPaiement   = signal<string>('');          // liste déroulante

  // ---------- Helpers ----------
  private normalize(s: unknown): string {
    return String(s ?? '')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/œ/g, 'oe').replace(/æ/g, 'ae').replace(/ß/g, 'ss')
      .replace(/[\u2019\u2018’]/g, "'")
      .toLowerCase()
      .trim();
  }

  // Options dynamiques extraites des données (triées, uniques, non vides)
  private uniqueSorted(values: (string | null | undefined)[]): string[] {
    const set = new Set(values.filter(v => !!v).map(v => String(v)));
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'fr'));
  }

  readonly optionsStatutPaiement = computed<string[]>(() =>
    [''].concat(this.uniqueSorted(this.leases().map(l => l?.statut_paiement)))
  );

  readonly optionsStatutPenalite = computed<string[]>(() =>
    [''].concat(this.uniqueSorted(this.leases().map(l => l?.statut_penalite)))
  );

  readonly optionsPayePar = computed<string[]>(() =>
    [''].concat(this.uniqueSorted(this.leases().map(l => l?.paye_par)))
  );

  readonly optionsStationPaiement = computed<string[]>(() =>
    [''].concat(this.uniqueSorted(this.leases().map(l => l?.station_paiement)))
  );

  // ---------- Liste filtrée ----------
  readonly filtered = computed<Lease[]>(() => {
    const rows = this.leases();
    if (!rows?.length) return [];

    const q   = this.normalize(this.query());
    const f1  = this.statutPaiement();
    const f2  = this.statutPenalite();
    const f3  = this.payePar();
    const f4  = this.stationPaiement();

    return rows.filter(l => {
      // Recherche multi-champs (insensible casse/accents) sur 4 champs
      let okSearch = true;
      if (q) {
        const a = this.normalize(l?.chauffeur_unique_id);
        const b = this.normalize(l?.chauffeur_nom);
        const c = this.normalize(l?.moto_unique_id);
        const d = this.normalize(l?.moto_vin);
        okSearch = a.includes(q) || b.includes(q) || c.includes(q) || d.includes(q);
      }

      // Filtres exacts si sélectionnés ('' = tous)
      const okStatutPaiement  = !f1 || String(l?.statut_paiement ?? '') === f1;
      const okStatutPenalite  = !f2 || String(l?.statut_penalite ?? '') === f2;
      const okPayePar         = !f3 || String(l?.paye_par ?? '') === f3;
      const okStationPaiement = !f4 || String(l?.station_paiement ?? '') === f4;

      return okSearch && okStatutPaiement && okStatutPenalite && okPayePar && okStationPaiement;
    });
  });

  // ---------- Pagination ----------
  readonly pageSize   = signal(50);
  readonly pageIndex  = signal(0);
  readonly total      = computed(() => this.filtered().length);
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly pageStart  = computed(() => this.pageIndex() * this.pageSize());
  readonly pageEnd    = computed(() => Math.min(this.pageStart() + this.pageSize(), this.total()));
  readonly paged      = computed(() => this.filtered().slice(this.pageStart(), this.pageEnd()));

  private _keepInRange = effect(() => {
    if (this.pageIndex() > this.totalPages() - 1) this.pageIndex.set(0);
  });

  readonly visiblePages = computed<PageItem[]>(() => {
    const total = this.totalPages();
    const current = this.pageIndex();
    const last = total - 1;
    const around = 1;
    const out: PageItem[] = [];
    const addRange = (s: number, e: number) => { for (let i = s; i <= e; i++) out.push({ type: 'page', index: i }); };

    if (total <= 7) { addRange(0, last); return out; }

    out.push({ type: 'page', index: 0 });
    let s = Math.max(1, current - around);
    let e = Math.min(last - 1, current + around);
    if (s > 1) out.push({ type: 'dots' });
    addRange(s, e);
    if (e < last - 1) out.push({ type: 'dots' });
    out.push({ type: 'page', index: last });
    return out;
  });

  goToPage(i: number) {
    const clamped = Math.max(0, Math.min(i, this.totalPages() - 1));
    this.pageIndex.set(clamped);
  }
  prev(){ this.goToPage(this.pageIndex() - 1); }
  next(){ this.goToPage(this.pageIndex() + 1); }
  changePageSize(size: number){ this.pageSize.set(size); this.pageIndex.set(0); }

  // ---------- Utils ----------
  trackByLease = (_: number, l: Lease) => l?.id ?? `${l?.chauffeur_unique_id}-${l?.moto_unique_id}`;
  clearFilters() {
    this.query.set('');
    this.statutPaiement.set('');
    this.statutPenalite.set('');
    this.payePar.set('');
    this.stationPaiement.set('');
    this.pageIndex.set(0);
  }
}
