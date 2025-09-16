import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG, ApiConfig } from '../core/api-config.token';
import { ContratChauffeur } from '../models/contrat-chauffeur.model';
import { catchError, finalize, of, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ContratChauffeurService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  private readonly _contratsCh = signal<ContratChauffeur[]>([]);
  private readonly _isLoadingContratCh = signal(false);
  private readonly _errorContratCh = signal<string | null>(null);

  // Etats de soumission (ajoutés)
  private readonly _isContratChSubmitting = signal<boolean>(false);
  private readonly _isContratChSubmitError = signal<string | null>(null);

  readonly contratsCh = this._contratsCh.asReadonly();
  readonly isLoadingContrat = this._isLoadingContratCh.asReadonly();
  readonly errorContrat = this._errorContratCh.asReadonly();

  // Exposition des états de soumission
  readonly isContratChSubmitting = this._isContratChSubmitting.asReadonly();
  readonly isContratChSubmitError = this._isContratChSubmitError.asReadonly();

  /** Fetch principal (json-server) */
  fetchContratChauffeur(): void {
    this._isLoadingContratCh.set(true);
    this._errorContratCh.set(null);

    this.http.get<ContratChauffeur[]>(`${this.config.apiUrl}/contratsCh`)
      .pipe(
        tap(res => this._contratsCh.set(res)),
        catchError(err => {
          this._errorContratCh.set(err?.error?.detail ?? 'Erreur lors du chargement.');
          return of([] as ContratChauffeur[]);
        }),
        finalize(() => this._isLoadingContratCh.set(false))
      )
      .subscribe();
  }

  /** POST /contratsCh — création */
  registerContratChauffeur(payload: Omit<ContratChauffeur, 'id'>, onSuccess?: (res: ContratChauffeur) => void): void {
    this._isContratChSubmitting.set(true);
    this._isContratChSubmitError.set(null);

    this.http.post<ContratChauffeur>(`${this.config.apiUrl}/contratsCh`, payload)
      .pipe(
        tap(res => {
          const current = this._contratsCh();
          this._contratsCh.set([res, ...current]);
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de la création du contrat chauffeur.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isContratChSubmitError.set(msg);
          console.error('[CONTRAT CH CREATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isContratChSubmitting.set(false))
      )
      .subscribe();
  }

  /** PUT /contratsCh/:id — mise à jour complète */
  updateContratChauffeur(id: number, payload: Partial<ContratChauffeur>, onSuccess?: (res: ContratChauffeur) => void): void {
    this._isContratChSubmitting.set(true);
    this._isContratChSubmitError.set(null);

    this.http.put<ContratChauffeur>(`${this.config.apiUrl}/contratsCh/${id}`, payload)
      .pipe(
        tap(res => {
          const updated = this._contratsCh().map(c => c.id === id ? res : c);
          this._contratsCh.set(updated);
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de la mise à jour du contrat chauffeur.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isContratChSubmitError.set(msg);
          console.error('[CONTRAT CH UPDATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isContratChSubmitting.set(false))
      )
      .subscribe();
  }
}
