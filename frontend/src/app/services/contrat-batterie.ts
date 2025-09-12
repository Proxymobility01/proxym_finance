import {inject, Injectable, signal} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {API_CONFIG, ApiConfig} from '../core/api-config.token';
import {ContratBatterie} from '../models/contrat-batterie.model';
import {catchError, finalize, of, tap} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ContratBatterieService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG)


  private readonly _contratsBatt = signal<ContratBatterie[]>([]);
  private readonly _isLoadingContratBatt = signal(false);
  private readonly _errorContratBatt = signal<string | null>(null);

  private readonly _isSubmitting = signal<boolean>(false);
  private readonly _submitError = signal<string | null>(null);

  readonly contratsBatt = this._contratsBatt.asReadonly();
  readonly isLoadingContratBatt = this._isLoadingContratBatt.asReadonly();
  readonly errorContratBatt = this._errorContratBatt.asReadonly();

  readonly isContratBattSubmitting = this._isSubmitting.asReadonly();
  readonly isContratBattSubmitError = this._submitError.asReadonly();

  fetchContratBatterie(){
    this._isLoadingContratBatt.set(true);
    this._errorContratBatt.set(null);

    this.http.get<ContratBatterie[]>(`${this.config.apiUrl}/contrats-batteries`)
      .pipe(
        tap(res => this._contratsBatt.set(res)),
        catchError(err => {
              this._errorContratBatt.set(err?.error?.detail ?? 'Erreur lors du chargement.');
              return of([] as ContratBatterie[]);
    }),
      finalize(() => this._isLoadingContratBatt.set(false))
      )
      .subscribe()
  }

  registerContratBatterie(fd: FormData, onSuccess?: (res: ContratBatterie) => void) {
    this._isSubmitting.set(true);
    this._submitError.set(null);

    this.http.post<ContratBatterie>(`${this.config.apiUrl}/contrats-batteries`, fd)
      .pipe(
        tap(res => {
          const current = this._contratsBatt();
          this._contratsBatt.set([res, ...current]);
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de l’enregistrement du contrat batterie.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._submitError.set(msg);
          console.error('[CONTRAT BATT CREATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isSubmitting.set(false))
      )
      .subscribe();
  }

  updateContratBatterie(id: number, fd: FormData, onSuccess?: (res: ContratBatterie) => void) {
    this._isSubmitting.set(true);
    this._submitError.set(null);

    this.http.put<ContratBatterie>(`${this.config.apiUrl}/contrats-batterie/${id}/`, fd)
      .pipe(
        tap(res => {
          const updated = this._contratsBatt().map(c => c.id === id ? res : c);
          this._contratsBatt.set(updated);
          onSuccess?.(res);
        }),
        catchError(err => {
          let msg = 'Erreur lors de la mise à jour du contrat batterie.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._submitError.set(msg);
          console.error('[CONTRAT BATT UPDATE ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isSubmitting.set(false))
      )
      .subscribe();
  }
}
