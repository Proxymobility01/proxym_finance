import {inject, Injectable, signal} from '@angular/core';
import {HttpClient, HttpParams, HttpResponse} from '@angular/common/http';
import {API_CONFIG, ApiConfig} from '../core/api-config.token';
import {Contrat, Filters, Order, Pagination, Sorting} from '../models/contrat.model';
import {catchError, finalize, map, of, tap} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ContratService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG)

  private readonly _contrats = signal<Contrat[]>([])
  private readonly _isLoadingContrat = signal(false)
  private readonly _errorContract = signal<string | null>(null)

  readonly contrats = this._contrats.asReadonly();
  readonly isLoadingContrat = this._isLoadingContrat.asReadonly();
  readonly errorContract = this._errorContract.asReadonly();


  /**
   * URL du mock json-server. Si tu as déjà `apiUrl` et `wsUrl` dans ApiConfig,
   * ajoute-y un `mockUrl` (recommandé). Sinon on fallback sur localhost:3001.
   */
  private readonly baseUrl = (this.config as any).mockUrl ?? 'http://localhost:3000';
  private readonly resourceUrl = `${this.baseUrl}/contrats`;

  // --- TTL cache (optionnel)
  private readonly STALE_MS = 300_000; // 5 min
  private readonly _lastFetch = signal<number>(0);
  private _lastFilters: Filters | undefined;
  private _lastPagination: Pagination | undefined;
  private _lastSorting: Sorting | undefined;


  private readonly _total = signal<number>(0);      // total avant pagination
  private readonly _page = signal<number>(1);       // 1-based
  private readonly _pageSize = signal<number>(10);
  private readonly _pageCount = signal<number>(1);

  // --- exposés
  readonly total = this._total.asReadonly();
  readonly page = this._page.asReadonly();
  readonly pageSize = this._pageSize.asReadonly();
  readonly pageCount = this._pageCount.asReadonly();

  // --- helpers setters
  setPage(p: number) { this._page.set(Math.max(1, p)); }
  setPageSize(n: number) { this._pageSize.set(Math.max(1, n)); }

  /** Construit params json-server + mémorise la dernière requête pour refetch */
  private buildParams(filters?: Filters, pagination?: Pagination, sorting?: Sorting): HttpParams {
    this._lastFilters = filters ? { ...filters } : undefined;
    this._lastPagination = pagination ? { ...pagination } : undefined;
    this._lastSorting = sorting ? { ...sorting } : undefined;

    const page = pagination?.page ?? this._page();
    const limit = pagination?.page_size ?? this._pageSize();

    let params = new HttpParams()
      .set('_page', String(page))
      .set('_limit', String(limit));

    const sort = sorting?.sort ?? '';
    const order: Order = sorting?.order ?? 'asc';
    if (sort) {
      params = params.set('_sort', String(sort)).set('_order', order);
    }

    // recherche globale
    const q = (filters?.q ?? '').toString().trim();
    if (q) params = params.set('q', q);

    // filtres exacts
    if (filters?.status != null) params = params.set('status', String(filters.status));

    return params;
  }

  /** Fetch principal (json-server) */
  fetchContrats(filters?: Filters, pagination?: Pagination, sorting?: Sorting): void {
    this._isLoadingContrat.set(true);
    this._errorContract.set(null);

    const params = this.buildParams(filters, pagination, sorting);

    this.http.get<Contrat[]>(this.resourceUrl, {
      params,
      observe: 'response'
    })
      .pipe(
        map((res: HttpResponse<Contrat[]>) => {
          // total via header X-Total-Count
          const totalHeader = res.headers.get('X-Total-Count');
          const total = Number(totalHeader ?? res.body?.length ?? 0);
          const items = res.body ?? [];
          return { items, total };
        }),
        tap(({ items, total }) => {
          const page = Number(params.get('_page')) || 1;
          const limit = Number(params.get('_limit')) || 10;

          this._contrats.set(items);
          this._total.set(total);
          this._page.set(page);
          this._pageSize.set(limit);
          this._pageCount.set(Math.max(1, Math.ceil(total / limit)));
          this._lastFetch.set(Date.now());
        }),
        catchError(err => {
          const msg = err?.error?.detail || 'Erreur lors du chargement des contrats (mock).';
          this._errorContract.set(msg);
          console.error('[MOCK API ERROR]:', err);
          this._contrats.set([]);
          this._total.set(0);
          this._pageCount.set(1);
          return of(null);
        }),
        finalize(() => this._isLoadingContrat.set(false))
      )
      .subscribe();
  }

  /** 🔁 Refetch avec les derniers critères */
  refetch(): void {
    this.fetchContrats(this._lastFilters, this._lastPagination, this._lastSorting);
  }

  /** ⏳ Refetch si cache périmé */
  refetchIfStale(): void {
    const age = Date.now() - this._lastFetch();
    if (!this._contrats().length || age > this.STALE_MS) this.refetch();
  }

  ngOnDestroy(): void {
    // rien à nettoyer (pas de subs conservées)
  }

}
