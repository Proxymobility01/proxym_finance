import {inject, Injectable, signal} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {API_CONFIG, ApiConfig} from '../core/api-config.token';
import {PaiementPenalitePayload, Penalite} from '../models/penalite.model';
import {catchError, finalize, of, switchMap, tap} from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class PenaliteService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  private readonly _penalites = signal<Penalite[]>([]);
  private readonly _isLoadingPenalite = signal(false);
  private readonly _errorPenalite = signal<string | null>(null);
  private readonly _isPenaliteSubmitting = signal<boolean>(false);
  private readonly _isPenaliteSubmitError = signal<string | null>(null);

  readonly penalites = this._penalites.asReadonly();
  readonly isLoadingPenalite = this._isLoadingPenalite.asReadonly();
  readonly errorPenalite = this._errorPenalite.asReadonly();
  readonly isPenaliteSubmitting = this._isPenaliteSubmitting.asReadonly();
  readonly isPenaliteSubmitError = this._isPenaliteSubmitError.asReadonly();

  fetchPenalites(){
    this._isLoadingPenalite.set(true);
    this._errorPenalite.set(null);

    this.http.get<Penalite[]>(`${this.config.apiUrl}/penalites`)
      .pipe(
        tap(res => this._penalites.set(res)),
        catchError(err => {
          this._errorPenalite.set(err?.error?.detail ?? 'Erreur lors du chargement.');
          return of([] as Penalite[]);
        }),
        finalize(() => this._isLoadingPenalite.set(false)),
      )
      .subscribe()
  }

  // penalite.service.ts (extrait)
  registerPaiementPenalite(payload: PaiementPenalitePayload, onSuccess?: (res: Penalite) => void) {
    this._isPenaliteSubmitting.set(true);
    this._isPenaliteSubmitError.set(null);

    this.http.post<Penalite>(`${this.config.apiUrl}/paiements-penalites/`, payload)
      .pipe(
        tap((penalite) => {
          if (penalite) {
            const current = this._penalites();
            const next = current.map(p => p.id === penalite.id ? penalite : p);
            this._penalites.set(next);
            onSuccess?.(penalite);
          }
        }),
        catchError(err => {
          let msg = 'Erreur lors du paiement de la pénalité.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isPenaliteSubmitError.set(msg);
          console.error('[PENALITE PAY ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isPenaliteSubmitting.set(false)),
      )
      .subscribe();
  }


}
