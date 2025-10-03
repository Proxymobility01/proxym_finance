import { HttpClient } from "@angular/common/http";
import { inject, Injectable, signal } from "@angular/core";
import { API_CONFIG, ApiConfig } from "../api-config.token";
import { STORAGE_KEYS, LoginResponse } from "./auth.model";
import { catchError, map, of, tap } from "rxjs";

@Injectable({
  providedIn: "root",
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly config: ApiConfig = inject(API_CONFIG);

  private refreshScheduler: any = null; // 👈 intervalle pour auto-refresh

  // --- signals internes ---
  private readonly _accessToken = signal<string | null>(localStorage.getItem(STORAGE_KEYS.access));
  private readonly _refreshToken = signal<string | null>(localStorage.getItem(STORAGE_KEYS.refresh));
  private readonly _userId = signal<number | null>(localStorage.getItem(STORAGE_KEYS.userId) ? +localStorage.getItem(STORAGE_KEYS.userId)! : null);
  private readonly _nom = signal<string | null>(localStorage.getItem(STORAGE_KEYS.nom));
  private readonly _prenom = signal<string | null>(localStorage.getItem(STORAGE_KEYS.prenom));
  private readonly _role = signal<string | null>(localStorage.getItem(STORAGE_KEYS.role));

  // --- signaux readonly pour le reste de l’app ---
  readonly accessToken = this._accessToken.asReadonly();
  readonly refreshToken = this._refreshToken.asReadonly();
  readonly userId = this._userId.asReadonly();
  readonly nom = this._nom.asReadonly();
  readonly prenom = this._prenom.asReadonly();
  readonly role = this._role.asReadonly();

  private readonly _isLoginLoading = signal(false);
  private readonly _loginError = signal<string | null>(null);

  readonly isLoginLoading = this._isLoginLoading.asReadonly();
  readonly loginError = this._loginError.asReadonly();

  // 🔑 login
  login(email: string, password: string) {
    this._isLoginLoading.set(true);
    this._loginError.set(null);

    return this.http
      .post<LoginResponse>(`${this.config.apiUrl}/auth/token/`, { email, password })
      .pipe(
        tap({
          next: (res) => {
            this.storeTokens(res);
            this.startRefreshScheduler();
            this._isLoginLoading.set(false);
          },
          error: (err) => {
            let msg = "Erreur lors de la connexion.";
            if (err?.error?.detail) msg = err.error.detail;
            this._loginError.set(msg);
            this._isLoginLoading.set(false);
          },
        }),
      );
  }

  // 🔓 logout
  logout() {
    localStorage.removeItem(STORAGE_KEYS.access);
    localStorage.removeItem(STORAGE_KEYS.refresh);
    localStorage.removeItem(STORAGE_KEYS.userId);
    localStorage.removeItem(STORAGE_KEYS.nom);
    localStorage.removeItem(STORAGE_KEYS.prenom);
    localStorage.removeItem(STORAGE_KEYS.role);

    this._accessToken.set(null);
    this._refreshToken.set(null);
    this._userId.set(null);
    this._nom.set(null);
    this._prenom.set(null);
    this._role.set(null);

    this.stopRefreshScheduler(); // 👈 stop auto-refresh
  }

  // 👤 fullname
  fullname(): string {
    return [this._nom(), this._prenom()].filter(Boolean).join(" ");
  }

  // 🔄 refresh token manuel
  refresh() {
    const refreshToken = this._refreshToken();
    if (!refreshToken) return of(null);

    return this.http
      .post<{ access: string }>(`${this.config.apiUrl}/auth/token/refresh/`, {
        refresh: refreshToken,
      })
      .pipe(
        tap((res) => {
          if (res?.access) {
            localStorage.setItem(STORAGE_KEYS.access, res.access);
            this._accessToken.set(res.access);
          }
        }),
        catchError((err) => {
          console.error("[REFRESH ERROR]", err);
          this.logout();
          return of(null);
        })
      );
  }

  // --- Helpers ---
  isLoggedIn(): boolean {
    return !!this._accessToken();
  }

  getRole(): string | null {
    return this._role();
  }

  getToken(): string | null {
    return this._accessToken();
  }

  // --- Private methods ---
  private storeTokens(res: LoginResponse) {
    localStorage.setItem(STORAGE_KEYS.access, res.access);
    localStorage.setItem(STORAGE_KEYS.refresh, res.refresh);
    localStorage.setItem(STORAGE_KEYS.userId, res.id.toString());
    localStorage.setItem(STORAGE_KEYS.nom, res.nom);
    localStorage.setItem(STORAGE_KEYS.prenom, res.prenom);
    localStorage.setItem(STORAGE_KEYS.role, res.role);

    this._accessToken.set(res.access);
    this._refreshToken.set(res.refresh);
    this._userId.set(res.id);
    this._nom.set(res.nom);
    this._prenom.set(res.prenom);
    this._role.set(res.role);
  }

  // --- Auto-refresh scheduler ---
  private startRefreshScheduler() {
    this.stopRefreshScheduler(); // au cas où

    // 🔄 ACCESS_TOKEN_LIFETIME = 55 min → on rafraîchit à 50 min
    const interval = 50 * 60 * 1000; // 50 minutes en ms

    this.refreshScheduler = setInterval(() => {
      if (this.isLoggedIn()) {
        this.refresh().subscribe();
      }
    }, interval);
  }

  private stopRefreshScheduler() {
    if (this.refreshScheduler) {
      clearInterval(this.refreshScheduler);
      this.refreshScheduler = null;
    }
  }
}
