import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG, ApiConfig } from '../core/api-config.token';
import {CombinedExportFilters, Lease, LeaseFilters, PaiementLeasePayload} from '../models/lease.model';
import {catchError, finalize, forkJoin, map, of, tap} from 'rxjs';
type FetchOptions = { all?: boolean; page?: number; pageSize?: number };
@Injectable({
  providedIn: 'root'
})
export class LeaseService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  // State interne (Signals)
  private readonly _isLeaseSubmitting = signal<boolean>(false);
  private readonly _isLeaseSubmitError = signal<string | null>(null);


  readonly isLeaseSubmitting = this._isLeaseSubmitting.asReadonly();
  readonly isLeaseSubmitError = this._isLeaseSubmitError.asReadonly();

  // =============================
  //        SIGNAUX INTERNES
  // =============================
  private readonly _leases            = signal<Lease[]>([]);
  private readonly _isLoadingLeases   = signal<boolean>(false);
  private readonly _errorLeases       = signal<string | null>(null);

  // Agrégats hors pagination (meta.totals)
  private readonly _totalPaidAmount    = signal<number>(0);
  private readonly _totalPaidCount     = signal<number>(0);
  private readonly _totalNonPaidAmount = signal<number>(0);
  private readonly _totalNonPaidCount  = signal<number>(0);
  private readonly _totalOverallAmount = signal<number>(0);
  private readonly _totalOverallCount  = signal<number>(0);

  // Pagination backend (renvoyée par DRF)
  private readonly _backendCount    = signal<number>(0);
  private readonly _backendNext     = signal<string | null>(null);
  private readonly _backendPrevious = signal<string | null>(null);

  // =============================
  //     EXPOSITION READONLY
  // =============================
  readonly leases          = this._leases.asReadonly();
  readonly isLoadingLeases = this._isLoadingLeases.asReadonly();
  readonly errorLeases     = this._errorLeases.asReadonly();

  readonly totalPaidAmount    = this._totalPaidAmount.asReadonly();
  readonly totalPaidCount     = this._totalPaidCount.asReadonly();
  readonly totalNonPaidAmount = this._totalNonPaidAmount.asReadonly();
  readonly totalNonPaidCount  = this._totalNonPaidCount.asReadonly();
  readonly totalOverallAmount = this._totalOverallAmount.asReadonly();
  readonly totalOverallCount  = this._totalOverallCount.asReadonly();
  private readonly _lastQueryKey = signal<string>('');
  readonly backendCount    = this._backendCount.asReadonly();
  readonly backendNext     = this._backendNext.asReadonly();
  readonly backendPrevious = this._backendPrevious.asReadonly();private readonly _lastFilters = signal<LeaseFilters>({});
  private readonly _lastOptions = signal<FetchOptions>({});

  private readonly _currentPage = signal<number>(1);
  private readonly _pageSize    = signal<number>(50);

// Exposition lecture seule
  readonly currentPage = this._currentPage.asReadonly();
  readonly pageSize    = this._pageSize.asReadonly();




  private todayISO(): string {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }



  fetchLeases(filters: LeaseFilters = {}, options: FetchOptions & { force?: boolean } = {}) {
    // mémorise les derniers filtres/options (avec défauts de pagination)
    const page     = options.page ?? this._currentPage();
    const pageSize = options.pageSize ?? this._pageSize();

    this._lastFilters.set({ ...filters });
    this._lastOptions.set({ ...options, page, pageSize });
    this._currentPage.set(page);
    this._pageSize.set(pageSize);

    this._isLoadingLeases.set(true);
    this._errorLeases.set(null);

    const qp = new URLSearchParams();

    // --- filtres texte/global ---
    if (filters.q)        qp.append('q', String(filters.q));
    if (filters.statut)   qp.append('statut', String(filters.statut));
    if (filters.paye_par) qp.append('paye_par', String(filters.paye_par));
    if (filters.station)  qp.append('station', String(filters.station));

    // --- date_concernee ---
    if (filters.date_concernee)        qp.append('date_concernee', filters.date_concernee);
    if (filters.date_concernee_after)  qp.append('date_concernee_after', filters.date_concernee_after);
    if (filters.date_concernee_before) qp.append('date_concernee_before', filters.date_concernee_before);

    // --- created (par défaut = today si all !== true) ---
    const shouldApplyCreated = !(options.all === true);
    const created = filters.created ?? (shouldApplyCreated ? this.todayISO() : undefined);
    if (created) qp.append('created', created);
    if (shouldApplyCreated) {
      if (filters.created_after)  qp.append('created_after',  filters.created_after);
      if (filters.created_before) qp.append('created_before', filters.created_before);
    }

    // --- pagination backend ---
    qp.append('page', String(page));
    qp.append('page_size', String(pageSize));

    const url = `${this.config.apiUrl}/lease/combined?${qp.toString()}`;
    const key = `${url}|all=${!!options.all}`;
    if (!options.force && this._lastQueryKey() === key) {
      this._isLoadingLeases.set(false);
      return;
    }
    this._lastQueryKey.set(key);

    this.http.get<any>(url).pipe(
      map(res => {
        // --- META agrégats ---
        const totals   = res?.meta?.totals ?? {};
        const paid     = totals?.paid ?? {};
        const nonPaid  = totals?.non_paid ?? {};
        const overall  = totals?.overall ?? {};

        this._totalPaidAmount.set(Number(paid.amount ?? 0));
        this._totalPaidCount.set(Number(paid.count ?? 0));
        this._totalNonPaidAmount.set(Number(nonPaid.amount ?? 0));
        this._totalNonPaidCount.set(Number(nonPaid.count ?? 0));
        this._totalOverallAmount.set(Number(overall.amount ?? 0));
        this._totalOverallCount.set(Number(overall.count ?? 0));

        // --- META pagination ---
        this._backendCount.set(Number(res?.count ?? 0));
        this._backendNext.set(res?.next ?? null);
        this._backendPrevious.set(res?.previous ?? null);

        // --- Résultats ---
        const rows = res?.results ?? [];
        const mapped: Lease[] = rows.map((item: any): Lease => ({
          id: item.id,
          chauffeur_unique_id: '',
          chauffeur: item.chauffeur ?? '',
          moto_unique_id: item.moto_unique_id ?? '',
          moto_vin: item.moto_vin ?? '',
          montant_moto: item.montant_moto,
          montant_batterie: item.montant_batt,
          montant_total: item.montant_total,
          date_concernee: item.date_concernee ?? null,
          date_limite: item.date_limite ?? null,
          methode_paiement: item.methode_paiement ?? null,
          agenges: item.agences ?? 'N/A',
          statut_paiement: item.statut_paiement ?? 'INCONNU',
          statut_penalite: item.statut_penalite ?? 'N/A',
          paye_par: item.paye_par ?? 'N/A',
          created: item.created ?? '',
          source: item.source,
        }));

        return mapped;
      }),
      tap(list => this._leases.set(list)),
      catchError(err => {
        this._errorLeases.set(err?.error?.detail ?? 'Erreur lors du chargement des leases.');
        console.error('[LEASE COMBINED FETCH ERROR]:', err);
        return of([] as Lease[]);
      }),
      finalize(() => this._isLoadingLeases.set(false))
    ).subscribe();
  }


// === HELPERS DE PAGINATION SERVEUR ===
  goToPageBackend(page: number) {
    const safe = Math.max(1, Math.floor(page || 1));
    const f = this._lastFilters();
    const o = this._lastOptions();
    this.fetchLeases(f, { ...o, page: safe });
  }

  nextPageBackend() {
    // on avance seulement si le backend expose "next"
    if (this._backendNext()) {
      this.goToPageBackend(this._currentPage() + 1);
    }
  }

  prevPageBackend() {
    if (this._backendPrevious()) {
      this.goToPageBackend(Math.max(1, this._currentPage() - 1));
    }
  }

  setPageSizeBackend(size: number) {
    const s = Math.max(1, Math.floor(size || 50));
    const f = this._lastFilters();
    const o = this._lastOptions();
    // reset à page 1 quand on change le pageSize
    this.fetchLeases(f, { ...o, page: 1, pageSize: s });
  }

  downloadCSV(filters: CombinedExportFilters = {}) {
    const qp = new URLSearchParams();

    if (filters.q) qp.append('q', filters.q);
    if (filters.statut) qp.append('statut', filters.statut);
    if (filters.paye_par) qp.append('paye_par', filters.paye_par);
    if (filters.station) qp.append('station', filters.station);

    if (filters.date_concernee)        qp.append('date_concernee', filters.date_concernee);
    if (filters.date_concernee_after)  qp.append('date_concernee_after', filters.date_concernee_after);
    if (filters.date_concernee_before) qp.append('date_concernee_before', filters.date_concernee_before);

    // created ne s’applique qu’aux PAYÉS, garde ta même logique que la liste
    if (filters.created) qp.append('created', filters.created);
    if (filters.created_after) qp.append('created_after', filters.created_after);
    if (filters.created_before) qp.append('created_before', filters.created_before);

    const url = `${this.config.apiUrl}/lease/combined/export/csv?${qp.toString()}`;
    return this.http.get(url, { responseType: 'blob' as const });
  }

  downloadXLSX(filters: CombinedExportFilters = {}) {
    const qp = new URLSearchParams();
    if (filters.q) qp.append('q', filters.q);
    if (filters.statut) qp.append('statut', filters.statut);
    if (filters.paye_par) qp.append('paye_par', filters.paye_par);
    if (filters.station) qp.append('station', filters.station);

    if (filters.date_concernee)        qp.append('date_concernee', filters.date_concernee);
    if (filters.date_concernee_after)  qp.append('date_concernee_after', filters.date_concernee_after);
    if (filters.date_concernee_before) qp.append('date_concernee_before', filters.date_concernee_before);

    // created ne s’applique qu’aux PAYÉS, garde ta même logique que la liste
    if (filters.created) qp.append('created', filters.created);
    if (filters.created_after) qp.append('created_after', filters.created_after);
    if (filters.created_before) qp.append('created_before', filters.created_before);

    const url = `${this.config.apiUrl}/lease/combined/export/xlsx?${qp.toString()}`;
    return this.http.get(url, { responseType: 'blob' as const });
  }


  // registerLease sur le modèle de registerConge
  registerLease(payload: Omit<PaiementLeasePayload, 'id'>, onSuccess?: (res: Lease) => void) {
    this._isLeaseSubmitting.set(true);
    this._isLeaseSubmitError.set(null);

    this.http.post<Lease>(`${this.config.apiUrl}/lease/pay`, payload)
      .pipe(
        tap(res => {
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de l’enregistrement du lease.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isLeaseSubmitError.set(msg);
          console.error('[LEASE CREATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isLeaseSubmitting.set(false)),
      )
      .subscribe();
  }

}
