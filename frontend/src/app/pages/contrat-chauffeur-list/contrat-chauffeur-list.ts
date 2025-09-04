import { Component, DestroyRef, effect, inject, OnInit, signal, computed } from '@angular/core';
import { ContratService } from '../../services/contrat';
import { interval } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { DatePipe, NgClass } from '@angular/common';
import { HighlightPipe } from '../../shared/highlight-pipe';
import {NumberPipe} from '../../shared/number-pipe';

type DateFilterMode = 'today' | 'week' | 'month' | 'year' | 'specific' | 'range' | 'all';

@Component({
  selector: 'app-contrat-chauffeur-list',
  standalone: true,
  imports: [
    FormsModule,
    NgClass,
    HighlightPipe,
    DatePipe,
    NumberPipe
  ],
  templateUrl: './contrat-chauffeur-list.html',
  styleUrl: './contrat-chauffeur-list.css'
})
export class ContratChauffeurList implements OnInit {

  private readonly destroyRef = inject(DestroyRef);
  private readonly contratService = inject(ContratService);

  // --- états exposés du service
  readonly contrats = this.contratService.contrats;
  readonly isLoadingContrat = this.contratService.isLoadingContrat;
  readonly error = this.contratService.errorContract;
  readonly total = this.contratService.total;
  readonly page = this.contratService.page;
  readonly pageSizeSig = this.contratService.pageSize;
  readonly pageCount = this.contratService.pageCount;

  // --- états locaux (filtres/tri)
  readonly search = signal('');
  readonly status = signal<'' | 'true' | 'false'>('');
  readonly sort = signal<'date_signature' | 'reference' | ''>('date_signature');
  readonly order = signal<'asc' | 'desc'>('desc');

  // --- filtre par période
  readonly dateMode = signal<DateFilterMode>('all');
  readonly dateSpecific = signal<string>(''); // YYYY-MM-DD
  readonly dateStart = signal<string>('');    // YYYY-MM-DD
  readonly dateEnd = signal<string>('');      // YYYY-MM-DD

  // --- liste affichée = contrats() filtrés par période (sur la page courante)
  readonly displayedContrats = computed(() => {
    const items = this.contrats();
    const mode = this.dateMode();
    if (mode === 'all') return items;

    const toDate = (s: string) => new Date(s + (s?.length === 10 ? 'T00:00:00' : ''));
    const today = new Date();
    const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const endOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);

    let from = new Date(0), to = new Date(8640000000000000);

    switch (mode) {
      case 'today': {
        const s = startOf(today), e = endOf(today); from = s; to = e; break;
      }
      case 'week': {
        const s = startOf(today);
        const day = s.getDay();                 // 0=dimanche
        const diff = (day === 0 ? 6 : day - 1); // lundi=0
        s.setDate(s.getDate() - diff);
        const e = endOf(new Date(s));
        e.setDate(s.getDate() + 6);
        from = s; to = e; break;
      }
      case 'month': {
        const s = new Date(today.getFullYear(), today.getMonth(), 1);
        const e = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59, 999);
        from = s; to = e; break;
      }
      case 'year': {
        const s = new Date(today.getFullYear(), 0, 1);
        const e = new Date(today.getFullYear(), 11, 31, 23, 59, 59, 999);
        from = s; to = e; break;
      }
      case 'specific': {
        if (!this.dateSpecific()) return items;
        const s = startOf(toDate(this.dateSpecific()));
        const e = endOf(toDate(this.dateSpecific()));
        from = s; to = e; break;
      }
      case 'range': {
        if (!this.dateStart() || !this.dateEnd()) return items;
        const s = startOf(toDate(this.dateStart()));
        const e = endOf(toDate(this.dateEnd()));
        from = s; to = e; break;
      }
    }

    return items.filter(c => {
      const d = new Date(c.date_signature);
      return d >= from && d <= to;
    });
  });

  // --- UI
  readonly expandedRowIndex = signal<number | null>(null);

  ngOnInit() {
    // 1er chargement
    this.contratService.fetchContrats(
      { q: null, status: null },
      { page: 1, page_size: this.pageSizeSig() },
      { sort: this.sort(), order: this.order() }
    );

    // rafraîchissement TTL
    interval(60_000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.contratService.refetchIfStale());
  }

  constructor() {
    // Recharger quand filtres/tri de base changent (repart à la page 1)
    let firstRun = true;
    effect(() => {
      this.search();
      this.status();
      this.sort();
      this.order();
      if (firstRun) { firstRun = false; return; }
      this.goToPage(1);
    });

    // Fermer la ligne étendue dès que la liste change
    effect(() => {
      this.contrats();
      this.expandedRowIndex.set(null);
    });
  }

  // --- normalisation recherche
  normalizeSearch(str: string): string {
    return (str ?? '')
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
  }

  // --- fetch helper
  private load(page: number) {
    const q = this.normalizeSearch(this.search());
    this.contratService.fetchContrats(
      {
        q: q || null,
        status: this.status() === '' ? null : this.status() === 'true'
      },
      { page, page_size: this.pageSizeSig() },
      { sort: this.sort() || undefined, order: this.order() }
    );
  }

  // --- pagination
  goToPage(page: number) {
    if (page < 1 || page > this.pageCount()) return;
    this.contratService.setPage(page);
    this.load(page);
  }
  goToNextPage() { this.goToPage(this.page() + 1); }
  goToPreviousPage() { this.goToPage(this.page() - 1); }
  changePageSize(n: number) {
    this.contratService.setPageSize(n);
    this.goToPage(1);
  }

  // --- tri
  toggleOrder() {
    this.order.set(this.order() === 'asc' ? 'desc' : 'asc');
  }

  // --- période
  setDateMode(mode: DateFilterMode) {
    this.dateMode.set(mode);
    if (mode !== 'specific') this.dateSpecific.set('');
    if (mode !== 'range') { this.dateStart.set(''); this.dateEnd.set(''); }
    // filtrage côté front → on repart à la page 1 pour cohérence UI
    this.goToPage(1);
  }

  // --- actions table
  toggleDetailsAt(i: number) {
    this.expandedRowIndex.set(this.expandedRowIndex() === i ? null : i);
  }
  isRowExpanded(i: number) { return this.expandedRowIndex() === i; }

  // --- exports
  exportCSV() {
    const rows = this.displayedContrats().map(c => ({
      reference: c.reference,
      nom_chauffeur: c.nom_chauffeur,
      date_signature: c.date_signature,
      montant_paye: c.montant_paye,
      montant_restant: c.montant_restant,
      montant_total: c.montant_total,
      status: c.status ? 'Terminé' : 'En cours',
    }));

    const headers = Object.keys(rows[0] ?? {
      reference:'', nom_chauffeur:'', date_signature:'', montant_paye:'', montant_restant:'', montant_total:'', status:''
    });

    const csv = [
      headers.join(';'),
      ...rows.map(r => headers.map(h => String((r as any)[h]).replace(/;/g, ',')).join(';'))
    ].join('\n');

    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `contrats_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async exportExcel() {
    // npm i xlsx
    const XLSX = await import('xlsx');
    const data = this.displayedContrats().map(c => ({
      Référence: c.reference,
      Chauffeur: c.nom_chauffeur,
      Date: c.date_signature,
      Payé: c.montant_paye,
      Restant: c.montant_restant,
      'Montant total': c.montant_total,
      Statut: c.status ? 'Terminé' : 'En cours',
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Contrats');
    XLSX.writeFile(wb, `contrats_${new Date().toISOString().slice(0,10)}.xlsx`);
  }

  // --- boutons "Action" (stubs)
  onViewContrat(c: any) {
    // TODO: dialog ou navigation
    console.log('view', c);
  }
  onEditContrat(c: any) {
    // TODO: dialog ou navigation
    console.log('edit', c);
  }

  // --- reset
  resetFilters() {
    this.search.set('');
    this.status.set('');
    this.sort.set('date_signature');
    this.order.set('desc');
    this.dateMode.set('all');
    this.dateSpecific.set('');
    this.dateStart.set('');
    this.dateEnd.set('');
    this.contratService.setPageSize(10);
    this.goToPage(1);
  }
}
