import {inject, Injectable, signal} from '@angular/core';
import {HttpClient } from '@angular/common/http';
import {API_CONFIG, ApiConfig} from '../core/api-config.token';
import {ContratChauffeur} from '../models/contrat-chauffeur.model';
import {catchError, finalize, of, tap} from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class ContratChauffeurService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG)

  private readonly _contratsCh = signal<ContratChauffeur[]>([])
  private readonly _isLoadingContratCh = signal(false)
  private readonly _errorContratCh = signal<string | null>(null)

  readonly contratsCh = this._contratsCh.asReadonly();
  readonly isLoadingContrat = this._isLoadingContratCh.asReadonly();
  readonly errorContrat = this._errorContratCh.asReadonly();



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
      .subscribe()


  }

}
