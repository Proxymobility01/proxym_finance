import {inject, Injectable, signal} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {API_CONFIG, ApiConfig} from "../core/api-config.token";
import { Garant} from "../models/garant.model";
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

  readonly garants = this._garants.asReadonly();
  readonly isLoadingGarant = this._isLoadingGarant.asReadonly();
  readonly errorGarant = this._errorGarant.asReadonly();


  fetchGarants() {
    this._isLoadingGarant.set(true);
    this._errorGarant.set(null)

    this.http.get<Garant[] >(`${this.config.apiUrl}/garants`)
        .pipe(
            tap(res => {this._garants.set(res);}),
            catchError(err => {
              this._errorGarant.set(err?.error?.detail ?? 'Erreur lors du chargement.');
              return of( [] as Garant[]);
            }),
            finalize(() => this._isLoadingGarant.set(false))
        )
        .subscribe()
  }

}
