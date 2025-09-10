import {inject, Injectable, signal} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {API_CONFIG, ApiConfig} from "../core/api-config.token";
import {Garant, GarantPayload} from "../models/garant.model";
import {catchError, finalize, of, tap} from "rxjs";

@Injectable({
  providedIn: 'root'
})
export class GarantService {
  private readonly http = inject(HttpClient)
  private readonly config: ApiConfig = inject(API_CONFIG)


  private readonly _garants = signal<Garant[]>([]);
  private readonly _isLoadingGarant = signal<boolean>(false);
  private readonly _errorGarant = signal<string | null>(null);
  private readonly _isGarantSubmitting = signal<boolean>(false);
  private readonly _isGarantSubmitError = signal<string | null>(null);

  readonly garants = this._garants.asReadonly();
  readonly isLoadingGarant = this._isLoadingGarant.asReadonly();
  readonly errorGarant = this._errorGarant.asReadonly();
  readonly isGarantSubmitting = this._isGarantSubmitting.asReadonly();
  readonly isGarantSubmitError = this._isGarantSubmitError.asReadonly();


  fetchGarants() {
    this._isLoadingGarant.set(true);
    this._errorGarant.set(null)

    this.http.get<Garant[]>(`${this.config.apiUrl}/garants/`)
      .pipe(
        tap(res => {
          this._garants.set(res);
        }),
        catchError(err => {
          this._errorGarant.set(err?.error?.detail ?? 'Erreur lors du chargement.');
          return of([] as Garant[]);
        }),
        finalize(() => this._isLoadingGarant.set(false))
      )
      .subscribe()
  }



  registerGarant(fd: FormData, onSuccess?: (res: Garant) => void) {
    this._isGarantSubmitting.set(true);
    this._isGarantSubmitError.set(null);

    this.http.post<Garant>(`${this.config.apiUrl}/garants/`, fd)
      .pipe(
        tap(res => {
          const current = this._garants();
          this._garants.set([res, ...current]);
          onSuccess?.(res);
        }),
        catchError(err => {
          // Améliore le message d’erreur pour les 400 DRF avec détails champ par champ
          let msg = 'Erreur lors de l’enregistrement du garant.';
          const e = err?.error;
          if (e?.detail) msg = e.detail;
          else if (e && typeof e === 'object') {
            msg = Object.entries(e)
              .map(([k, v]: any) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
              .join(' | ');
          }
          this._isGarantSubmitError.set(msg);
          console.error('[GARANT API ERROR]:', err);
          return of(null);
        }),
        finalize(() => this._isGarantSubmitting.set(false))
      )
      .subscribe();
  }

}
