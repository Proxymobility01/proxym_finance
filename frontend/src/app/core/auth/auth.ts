import { HttpClient } from "@angular/common/http";
import { computed, inject, Injectable, signal, effect } from "@angular/core";
import { AUTH_API_CONFIG, API_CONFIG, ApiConfig } from "../api-config.token";
import { AuthResponse, RefreshResponse, LocalProfile } from "./auth.model";
import { catchError, concatMap, of, switchMap, tap, Observable, timer, Subscription } from "rxjs";
import { Router } from "@angular/router";

@Injectable({
  providedIn: "root",
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly authApiConfig: ApiConfig = inject(AUTH_API_CONFIG);
  private readonly ApiConfig: ApiConfig = inject(API_CONFIG);
  private readonly router = inject(Router);

  // --- Signaux internes ---
  private readonly _accessToken = signal<string | null>(null);
  private readonly _currentUser = signal<LocalProfile | null>(null);
  private readonly _authReady = signal<boolean>(false);
  private refreshSub?: Subscription; // timer de rafraîchissement

  private readonly _isLoginLoading = signal<boolean>(false);
  private readonly _loginError = signal<string | null>(null);
  readonly isLoginLoading = this._isLoginLoading.asReadonly();
  readonly loginError = this._loginError.asReadonly();

  // --- Signaux publics ---
  readonly accessToken = this._accessToken.asReadonly();
  readonly currentUser = this._currentUser.asReadonly();
  readonly authReady = this._authReady.asReadonly();

  readonly isLoggedIn = computed(() => !!this._accessToken() && !!this._currentUser());

  readonly fullname = computed(() => {
    const profile = this._currentUser();
    return profile ? `${profile.prenom || ''} ${profile.nom || ''}`.trim() : 'Utilisateur';
  });

  readonly role = computed(() => this._currentUser()?.role?.nomRole || null);



  // ✅ Initialisation du flux auth
  initAuth(): Observable<any> {
    return this.refreshAndGetProfile().pipe(
      tap(() => console.log("✅ Restauration de session réussie")),
      catchError((err) => {
        // C'est ici que tu verras pourquoi ça échoue (CORS, Cookie manquant, 401...)
        console.error("❌ Échec de la restauration de session :", err);
        this.clearAuth();
        // On retourne of(null) pour ne pas faire planter le démarrage de l'app,
        // l'utilisateur sera juste considéré comme déconnecté.
        return of(null);
      }),
      tap(() => this._authReady.set(true)) // On signale que l'auth est finie (succès ou échec)
    );
  }

  // ✅ Login complet
  login(email: string, password: string): Observable<LocalProfile> {
    const body = { login: email, password: password };

    return this.http
      .post<AuthResponse>(`${this.authApiConfig.apiUrl}/auth/token/`, body, {
        withCredentials: true
      })
      .pipe(
        switchMap((authRes) => {
          this._accessToken.set(authRes.access);
          this.scheduleTokenRefresh(authRes.access); // 🕒 planifie le refresh
          return this.getLocalProfile();
        }),
        tap({
          next: (profile) => this._currentUser.set(profile),
          error: () => this.clearAuth()
        })
      );
  }

  // ✅ Logout
  logout(): Observable<any> {
    // Retourne l'observable — ne pas faire .subscribe() ici
    return this.http
      .post(`${this.authApiConfig.apiUrl}/auth/logout/`, {}, {
        withCredentials: true // Nécessaire pour envoyer le cookie refresh_token
      })
      .pipe(
        // en cas d'erreur on continue quand même (ex: backend unreachable)
        catchError(() => of(null)),
        tap(() => {
          this.clearAuth();
        })
      );
  }

  // ✅ Refresh automatique du token
  refresh(): Observable<RefreshResponse> {
    return this.http
      .post<RefreshResponse>(`${this.authApiConfig.apiUrl}/auth/token/refresh/`, {}, {
        withCredentials: true
      })
      .pipe(
        tap(res => {
          this._accessToken.set(res.access);
          this.scheduleTokenRefresh(res.access); // replanifie le timer à chaque refresh
        })
      );
  }

  getLocalProfile(): Observable<LocalProfile> {
    return this.http.get<LocalProfile>(`${this.ApiConfig.apiUrl}/auth/me/`).pipe(
      tap(profile => this._currentUser.set(profile))
    );
  }

  refreshAndGetProfile(): Observable<LocalProfile> {
    return this.refresh().pipe(concatMap(() => this.getLocalProfile()));
  }

  private clearAuth() {
    this._accessToken.set(null);
    this._currentUser.set(null);
    this._isLoginLoading.set(false);
    this._loginError.set(null);
    this.cancelScheduledRefresh();
  }

  getToken(): string | null {
    return this._accessToken();
  }

  /**
   * 🕒 Planifie un rafraîchissement 2 minutes avant expiration
   * (access_token = 7min → refresh à 5min)
   */
  private scheduleTokenRefresh(token: string) {
    this.cancelScheduledRefresh(); // évite les doublons
    const refreshBeforeMs = 5 * 60 * 1000; // on rafraîchit à 5 minutes

    this.refreshSub = timer(refreshBeforeMs).pipe(
      switchMap(() => this.refresh())
    ).subscribe({
      next: () => console.log('🔄 Access token rafraîchi automatiquement'),
      error: (err) => {
        console.error('Erreur lors du refresh automatique', err);
        this.clearAuth();
      }
    });
  }

  private cancelScheduledRefresh() {
    if (this.refreshSub) {
      this.refreshSub.unsubscribe();
      this.refreshSub = undefined;
    }
  }


}
