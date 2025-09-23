import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG, ApiConfig } from '../core/api-config.token';
import {Conge, CongeCreatePayload, CongePayload, CongeUpdatePayload} from '../models/conge.model';
import { catchError, finalize, of, tap } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class CongeService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  private readonly _conges = signal<Conge[]>([]);
  private readonly _isLoadingConge = signal<boolean>(false);
  private readonly _errorConge = signal<string | null>(null);
  private readonly _isCongeSubmitting = signal<boolean>(false);
  private readonly _isCongeSubmitError = signal<string | null>(null);

  readonly conges = this._conges.asReadonly();
  readonly isLoadingConge = this._isLoadingConge.asReadonly();
  readonly errorConge = this._errorConge.asReadonly();
  readonly isCongeSubmitting = this._isCongeSubmitting.asReadonly();
  readonly isCongeSubmitError = this._isCongeSubmitError.asReadonly();

  // ---- LIST
  fetchConges() {
    this._isLoadingConge.set(true);
    this._errorConge.set(null);

    this.http.get<Conge[]>(`${this.config.apiUrl}/conges`)
      .pipe(
        tap(res => this._conges.set(res ?? [])),
        catchError(err => {
          this._errorConge.set(err?.error?.detail ?? 'Erreur lors du chargement.');
          return of([] as Conge[]);
        }),
        finalize(() => this._isLoadingConge.set(false)),
      )
      .subscribe();
  }

  // ---- CREATE (JSON body)
  registerConge(payload: CongeCreatePayload, onSuccess?: (res: Conge) => void) {
    this._isCongeSubmitting.set(true);
    this._isCongeSubmitError.set(null);

    this.http.post<Conge>(`${this.config.apiUrl}/conges/`, payload)
      .pipe(
        tap(res => {
          const current = this._conges();
          this._conges.set([res, ...current]);
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de l’enregistrement du congé.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isCongeSubmitError.set(msg);
          console.error('[CONGE CREATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isCongeSubmitting.set(false)),
      )
      .subscribe();
  }

  // ---- UPDATE (JSON body)  -> PATCH conseillé si partiel, PUT si complet
  updateConge(id: number, payload: CongeUpdatePayload, onSuccess?: (res: Conge) => void) {
    this._isCongeSubmitting.set(true);
    this._isCongeSubmitError.set(null);

    // ⚠️ Ne jamais envoyer `contrat_id` en update
    const { contrat_id, ...safePayload } = payload as any;

    this.http.patch<Conge>(`${this.config.apiUrl}/conges/${id}/`, safePayload)
      .pipe(
        tap(res => {
          const current = this._conges();
          const updated = current.map(c => c.id === id ? res : c);
          this._conges.set(updated);
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de la mise à jour du congé.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isCongeSubmitError.set(msg);
          console.error('[CONGE UPDATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isCongeSubmitting.set(false)),
      )
      .subscribe();
  }


}
