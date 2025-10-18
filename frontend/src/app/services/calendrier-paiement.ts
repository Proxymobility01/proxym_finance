import { computed, inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, finalize, map, of, tap } from 'rxjs';
import { API_CONFIG, ApiConfig } from '../core/api-config.token';
import {ChauffeurCalendrierItem, PaginatedResponse} from '../models/calendrier.model';
export type FetchOptions = {
  page?: number;
  pageSize?: number;
  search?: string;
  append?: boolean;
};

@Injectable({ providedIn: 'root' })
export class CalendrierPaiementService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  // ⚠️ Ajuste le segment si ton endpoint diffère
  private readonly calendarEndpoint = '/lease/paiements/calendrier';

  // =============================
  //               STATE
  // =============================
  private readonly _items = signal<ChauffeurCalendrierItem[]>([]);
  private readonly _isLoading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);

  private readonly _count = signal<number>(0);
  private readonly _next = signal<string | null>(null);
  private readonly _previous = signal<string | null>(null);

  private readonly _currentPage = signal<number>(1);
  private readonly _pageSize = signal<number>(50);
  private readonly _searchTerm = signal<string>('');
  readonly hasMore = computed<boolean>(() => {
    // Deux stratégies possibles :
    // 1) via "next" du backend DRF
    if (this._next()) return true;
    // 2) sécurité via count/page/pageSize
    return this._currentPage() * this._pageSize() < this._count();
  });

  // Exposition lecture seule
  readonly items = this._items.asReadonly();
  readonly isLoading = this._isLoading.asReadonly();
  readonly error = this._error.asReadonly();

  readonly backendCount = this._count.asReadonly();
  readonly backendNext = this._next.asReadonly();
  readonly backendPrevious = this._previous.asReadonly();
  readonly currentPage = this._currentPage.asReadonly();
  readonly pageSize = this._pageSize.asReadonly();
  readonly searchTerm = this._searchTerm.asReadonly();

  // =============================
  //              FETCH
  // =============================
  fetchCalendrier(options: FetchOptions = {}) {
    const page = options.page ?? this._currentPage();
    const pageSize = options.pageSize ?? this._pageSize();
    const search = options.search ?? this._searchTerm();
    const append = !!options.append;

    this._isLoading.set(true);
    this._error.set(null);

    const qp = new URLSearchParams();
    qp.set('page', String(page));
    qp.set('page_size', String(pageSize));
    if (search?.trim()) qp.set('search', search.trim());

    const url = `${this.config.apiUrl}${this.calendarEndpoint}?${qp.toString()}`;

    this.http
      .get<PaginatedResponse<ChauffeurCalendrierItem>>(url)
      .pipe(
        tap((res) => {
          this._count.set(Number(res?.count ?? 0));
          this._next.set(res?.next ?? null);
          this._previous.set(res?.previous ?? null);
        }),
        map((res) => (res?.results ?? []) as ChauffeurCalendrierItem[]),
        tap((list) => {
          const normalized = list.map((it) => ({
            ...it,
            paiements: Array.isArray(it.paiements) ? it.paiements : [],
            conges: Array.isArray(it.conges) ? it.conges : [],
            paiements_par_jour: it.paiements_par_jour ?? {}, // 👈 nouveau champ
            resume: {
              total_jours: it.resume?.total_jours ?? 0,
              jours_payes: it.resume?.jours_payes ?? 0,
              jours_conges: it.resume?.jours_conges ?? 0,
              total_paiements: it.resume?.total_paiements ?? Object.values(it.paiements_par_jour ?? {}).reduce((a, b) => a + b, 0),
            },
          }));

          if (append && page > 1) {
            this._items.set([...this._items(), ...normalized]);
          } else {
            this._items.set(normalized);
          }

          this._currentPage.set(page);
          this._pageSize.set(pageSize);
          this._searchTerm.set(search);
        }),
        catchError((err) => {
          const msg =
            err?.error?.detail ||
            err?.message ||
            'Erreur lors du chargement du calendrier.';
          this._error.set(msg);
          console.error('[CALENDRIER FETCH ERROR]:', err);
          this._items.set([]);
          return of([] as ChauffeurCalendrierItem[]);
        }),
        finalize(() => this._isLoading.set(false))
      )
      .subscribe();
  }

  // =============================
  //       PAGINATION HELPERS
  // =============================
  goToPage(page: number) {
    const safe = Math.max(1, Math.floor(page || 1));
    this.fetchCalendrier({ page: safe });
  }

  nextPage() {
    if (this._next()) this.goToPage(this._currentPage() + 1);
  }

  prevPage() {
    if (this._previous()) this.goToPage(Math.max(1, this._currentPage() - 1));
  }

  setPageSize(size: number) {
    const s = Math.max(1, Math.floor(size || 50));
    this.fetchCalendrier({ page: 1, pageSize: s });
  }

  // =============================
  //            RECHERCHE
  // =============================
  searchCalendrier(term: string) {
    this.fetchCalendrier({ page: 1, search: term });
  }



}
