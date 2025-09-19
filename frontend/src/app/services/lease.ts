import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG, ApiConfig } from '../core/api-config.token';
import {Lease, PaiementLeasePayload} from '../models/lease.model';
import { catchError, finalize, of, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LeaseService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  // State interne (Signals)
  private readonly _leases = signal<Lease[]>([]);
  private readonly _isLoadingLeases = signal<boolean>(false);
  private readonly _errorLeases = signal<string | null>(null);
  private readonly _isLeaseSubmitting = signal<boolean>(false);
  private readonly _isLeaseSubmitError = signal<string | null>(null);

  // Exposition en lecture seule
  readonly leases = this._leases.asReadonly();
  readonly isLoadingLeases = this._isLoadingLeases.asReadonly();
  readonly errorLeases = this._errorLeases.asReadonly();
  readonly isLeaseSubmitting = this._isLeaseSubmitting.asReadonly();
  readonly isLeaseSubmitError = this._isLeaseSubmitError.asReadonly();

  // GET /leases/
  fetchLeases() {
    this._isLoadingLeases.set(true);
    this._errorLeases.set(null);

    this.http.get<Lease[]>(`${this.config.apiUrl}/lease/payments`)
      .pipe(
        tap((res) => this._leases.set(res)),
        catchError((err) => {
          this._errorLeases.set(err?.error?.detail ?? 'Erreur lors du chargement.');
          return of([] as Lease[]);
        }),
        finalize(() => this._isLoadingLeases.set(false))
      )
      .subscribe();
  }

  // registerLease sur le modèle de registerConge
  registerLease(payload: Omit<PaiementLeasePayload, 'id'>, onSuccess?: (res: Lease) => void) {
    this._isLeaseSubmitting.set(true);
    this._isLeaseSubmitError.set(null);

    this.http.post<Lease>(`${this.config.apiUrl}/leases/`, payload)
      .pipe(
        tap(res => {
          const current = this._leases();
          this._leases.set([res, ...current]);
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
