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

  readonly contratsBatt = this._contratsBatt.asReadonly();
  readonly isLoadingContratBatt = this._isLoadingContratBatt.asReadonly();
  readonly errorContratBatt = this._errorContratBatt.asReadonly();

  fetchContratBatterie(){
    this._isLoadingContratBatt.set(true);
    this._errorContratBatt.set(null);

    this.http.get<ContratBatterie[]>(`${this.config.apiUrl}/batteries`)
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
}
