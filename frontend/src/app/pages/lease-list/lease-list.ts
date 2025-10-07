

// src/app/pages/leases/lease-list.ts
import { Component, OnInit, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LeaseService } from '../../services/lease';
import {CombinedExportFilters, Lease, LeaseFilters} from '../../models/lease.model';
import { MatDialog } from '@angular/material/dialog';
import { AddPaiementLeaseComponent } from '../../components/add-paiement-lease/add-paiement-lease';
import { NumberPipe } from '../../shared/number-pipe';

type PageItem = { type: 'page'; index: number } | { type: 'dots' };
type DateFilterMode = 'none' | 'today' | 'specific' | 'range';

@Component({
  selector: 'app-lease-list',
  standalone: true,
  imports: [CommonModule, FormsModule, NumberPipe],
  templateUrl: './lease-list.html',
  styleUrls: ['./lease-list.css'],
})
export class LeaseList implements OnInit {
  private readonly leaseService = inject(LeaseService);
  private readonly dialog = inject(MatDialog);
  private readonly _lastParamsKey = signal<string>('');

  // ---------- Source ----------
  readonly leases      = this.leaseService.leases;           // 👈 déjà paginées par le backend
  readonly isLoading   = this.leaseService.isLoadingLeases;
  readonly error       = this.leaseService.errorLeases;

  // ---------- Totaux (hors pagination, renvoyés par l’API) ----------
  readonly totalPaidAmount    = this.leaseService.totalPaidAmount;    // number
  readonly totalPaidCount     = this.leaseService.totalPaidCount;     // number
  readonly totalNonPaidAmount = this.leaseService.totalNonPaidAmount; // number
  readonly totalNonPaidCount  = this.leaseService.totalNonPaidCount;  // number


  // ---------- Pagination backend ----------
  readonly backendCount  = this.leaseService.backendCount;   // total éléments filtrés (toutes pages)
  readonly currentPage   = this.leaseService.currentPage;    // page courante (1-based)
  readonly pageSize      = this.leaseService.pageSize;       // taille de page
  readonly totalPages    = computed(() => {
    const count = this.backendCount() || 0;
    const size  = this.pageSize() || 1;
    return Math.max(1, Math.ceil(count / size));
  });

  // Pages visibles (ui)
  readonly visiblePages = computed<PageItem[]>(() => {
    const total = this.totalPages();
    const current = (this.currentPage() - 1); // 0-based interne pour le calcul
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

  goToPage(iZeroBased: number) {
    const pageOneBased = iZeroBased + 1;
    this.leaseService.goToPageBackend(pageOneBased);
  }
  prev() { this.leaseService.prevPageBackend(); }
  next() { this.leaseService.nextPageBackend(); }
  setPageSize(size: number) { this.leaseService.setPageSizeBackend(size); }

  // =========================
  //        FILTRES
  // =========================

  // Recherche texte -> backend (?q=)
  readonly query = signal<string>('');

  // Statut global -> backend (?statut=) ; défaut PAYE
  readonly statutPaiement = signal<string>('');

  // back: ?paye_par= & ?station=
  readonly payePar = signal<string>('');
  readonly agencePaiement = signal<string>('');


  // Date CONCERNÉE — backend
  readonly dateModeConcernee = signal<DateFilterMode>('none');
  readonly dateSpecificConcernee = signal<string>(''); // YYYY-MM-DD
  readonly dateStartConcernee = signal<string>('');    // YYYY-MM-DD
  readonly dateEndConcernee = signal<string>('');      // YYYY-MM-DD

  // Date PAIEMENT (created) — backend (par défaut: today)
  readonly dateModeCreated = signal<DateFilterMode>('none');
  readonly dateSpecificCreated = signal<string>('');
  readonly dateStartCreated = signal<string>('');  // pour 'range'
  readonly dateEndCreated = signal<string>('');    // pour 'range'

  // Bypass ponctuel de l’effet (bouton “All”)
  private readonly bypassOnce = signal<boolean>(false);
  readonly allPayePar = signal<string[]>([]);
  readonly allAgences = signal<string[]>([]);


  // Helpers
  private todayISO(): string {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }
  private number(v: unknown): string {
    const n = Number(v ?? 0);
    return isFinite(n) ? n.toLocaleString('fr-FR') : '';
  }
  formatFCFA(n: number): string {
    return n.toLocaleString('fr-FR') + ' FCFA';
  }

  // Construction des query params (filters) pour le backend
  private buildBackendParams(): LeaseFilters | undefined {
    const params: any = {};

    const q = this.query().trim();
    if (q) params.q = q;

    const st = this.statutPaiement().trim();
    if (st) params.statut = st;

    const pp = this.payePar().trim();
    if (pp) params.paye_par = pp;

    const stn = this.agencePaiement().trim();
    if (stn) params.agence = stn;

    // Date concernée
    const modeCon = this.dateModeConcernee();
    const cSpec = this.dateSpecificConcernee().trim();
    const cStart = this.dateStartConcernee().trim();
    const cEnd   = this.dateEndConcernee().trim();
    if (modeCon === 'today') {
      params.date_concernee = this.todayISO();
    } else if (modeCon === 'specific' && cSpec) {
      params.date_concernee = cSpec;
    } else if (modeCon === 'range') {
      if (cStart) params.date_concernee_after = cStart;
      if (cEnd)   params.date_concernee_before = cEnd;
    }

    // Date paiement (created)
    const modeCre = this.dateModeCreated();
    const pSpec = this.dateSpecificCreated().trim();
    const pStart = this.dateStartCreated().trim();
    const pEnd   = this.dateEndCreated().trim();
    if (modeCre === 'today') {
      params.created = this.todayISO();
    } else if (modeCre === 'specific' && pSpec) {
      params.created = pSpec;
    } else if (modeCre === 'range') {
      if (pStart) params.created_after = pStart;
      if (pEnd)   params.created_before = pEnd;
    }
    // 'none' => rien

    return Object.keys(params).length ? params : undefined;
  }

  private _optionsSync = effect(() => {
    const leases = this.leases();
    if (!leases || leases.length === 0) return;

    const payeurs = Array.from(new Set(leases.map(l => l?.paye_par).filter(Boolean)));
    const agences = Array.from(new Set(leases.map(l => l?.agence).filter(Boolean)));

    // ✅ fusionner avec les anciennes pour ne pas perdre les anciennes valeurs
    this.allPayePar.update(prev => Array.from(new Set([...prev, ...payeurs])));
    this.allAgences.update(prev => Array.from(new Set([...prev, ...agences])));
  });

  // Effet: (re)fetch quand un filtre backend change
  private _backendSync = effect(() => {
    if (this.bypassOnce()) { this.bypassOnce.set(false); return; }

    // dépendances lues pour que l’effect réagisse
    void this.query();
    void this.statutPaiement();
    void this.payePar();
    void this.agencePaiement();
    void this.dateModeConcernee(); void this.dateSpecificConcernee(); void this.dateStartConcernee(); void this.dateEndConcernee();
    void this.dateModeCreated();   void this.dateSpecificCreated();   void this.dateStartCreated();   void this.dateEndCreated();
    void this.pageSize(); // si la taille de page change, on refetch

    const filters = this.buildBackendParams() ?? {};
    const allForCreated = (this.dateModeCreated() === 'none');
    const page = 1;
    const pageSize = this.pageSize();

    // 🔒 clé anti-doublon (si rien n’a changé, on ne rappelle pas l’API)
    const key = JSON.stringify({ filters, allForCreated, page, pageSize });
    if (this._lastParamsKey() === key) return;
    this._lastParamsKey.set(key);

    this.leaseService.fetchLeases(filters, { all: allForCreated, page, pageSize });
  });

  private uniqueSorted(values: (string | null | undefined)[]): string[] {
    const set = new Set(values.filter(v => !!v).map(v => String(v)));
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'fr'));
  }

  readonly optionsPayePar = computed<string[]>(() =>
    this.uniqueSorted(this.allPayePar())
  );
  readonly optionsAgencePaiement = computed<string[]>(() => {
    const names = this.uniqueSorted(this.allAgences());
    if (!names.includes('Direction')) names.unshift('Direction'); // 👈 ajoute l’option
    return names;
  });


  // Cycle de vie : l’effet déclenche le fetch initial (statut=PAYE + created=today)
  ngOnInit() {}

  // Actions UI
  fetchAll() {
    // empêcher l’effet de relancer un fetch avec des params
    this.bypassOnce.set(true);

    // vider tous les filtres
    this.query.set('');
    this.statutPaiement.set('');
    this.payePar.set('');
    this.agencePaiement.set('');

    this.dateModeConcernee.set('none');
    this.dateSpecificConcernee.set('');
    this.dateStartConcernee.set('');
    this.dateEndConcernee.set('');

    this.dateModeCreated.set('none');   // désactive created
    this.dateSpecificCreated.set('');
    this.dateStartCreated.set('');
    this.dateEndCreated.set('');

    // appel explicite en mode all (désactive created côté PAYÉS) + reset page=1
    this.leaseService.fetchLeases({}, { all: true, page: 1, pageSize: this.pageSize() });
  }

  clearFilters() {
    this.query.set('');
    this.statutPaiement.set('');
    this.payePar.set('');
    this.agencePaiement.set('');

    this.dateModeConcernee.set('none');
    this.dateSpecificConcernee.set('');
    this.dateStartConcernee.set('');
    this.dateEndConcernee.set('');

    this.dateModeCreated.set('none');
    this.dateSpecificCreated.set('');
    this.dateStartCreated.set('');
    this.dateEndCreated.set('');

  }

  openPaiementLeaseDialog() {
    this.dialog.open(AddPaiementLeaseComponent, {
      width: '90vw',
      maxWidth: '550px',
      panelClass: 'paiement-lease',
      disableClose: true,
    }).afterClosed().subscribe(res => {
      if (res) this.leaseService.fetchLeases({}, { all: true, page: 1, pageSize: this.pageSize() , force: true});
    });
  }

  getStatusPaiementClass(statut: string | undefined): string {
    if (!statut) return 'status-default';
    const normalized = statut.toLowerCase().replace(/\s+/g, '-');
    return `status-${normalized}`;
  }

  // lease-list.ts (dans le composant)
  private buildExportFilters(): CombinedExportFilters {
    const params: CombinedExportFilters = {};

    // texte & sélecteurs
    if (this.query().trim()) params.q = this.query().trim();
    if (this.statutPaiement().trim()) params.statut = this.statutPaiement().trim() as any;
    if (this.payePar().trim()) params.paye_par = this.payePar().trim();
    if (this.agencePaiement().trim()) params.agence = this.agencePaiement().trim();
    // date concernée
    if (this.dateModeConcernee() === 'today') {
      params.date_concernee = this.todayISO();
    } else if (this.dateModeConcernee() === 'specific' && this.dateSpecificConcernee().trim()) {
      params.date_concernee = this.dateSpecificConcernee().trim();
    } else if (this.dateModeConcernee() === 'range') {
      if (this.dateStartConcernee().trim())  params.date_concernee_after = this.dateStartConcernee().trim();
      if (this.dateEndConcernee().trim())    params.date_concernee_before = this.dateEndConcernee().trim();
    }

    // date paiement (created) — même règle que la liste
    if (this.dateModeCreated() === 'today') {
      params.created = this.todayISO();
    } else if (this.dateModeCreated() === 'specific' && this.dateSpecificCreated().trim()) {
      params.created = this.dateSpecificCreated().trim();
    } else if (this.dateModeCreated() === 'range') {
      if (this.dateStartCreated().trim()) params.created_after = this.dateStartCreated().trim();
      if (this.dateEndCreated().trim())   params.created_before = this.dateEndCreated().trim();
    }
    // 'none' => rien

    return params;
  }

  exportCSV() {
    const filters = this.buildExportFilters();
    this.leaseService.downloadCSV(filters).subscribe({
      next: (blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `leases_${new Date().toISOString().slice(0,10)}.csv`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(a.href);
        a.remove();
      },
      error: (err) => console.error('[EXPORT CSV ERROR]:', err),
    });
  }

  exportExcel() {
    const filters = this.buildExportFilters();
    this.leaseService.downloadXLSX(filters).subscribe({
      next: (blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `leases_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(a.href);
        a.remove();
      },
      error: (err) => console.error('[EXPORT XLSX ERROR]:', err),
    });
  }


}
