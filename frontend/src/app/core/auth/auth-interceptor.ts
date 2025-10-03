// src/app/auth/auth.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import {AuthService} from './auth';


let isRefreshing = false;

const AUTH_URLS_SKIP = [
  '/auth/token/',
  '/auth/token/refresh/',
  '/auth/logout/'
];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  const shouldSkip = AUTH_URLS_SKIP.some(u => req.url.includes(u));
  const token = auth.getToken();

  // Ajoute Authorization sauf pour les routes d’auth
  const authReq = token && !shouldSkip
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (shouldSkip) {
        return throwError(() => error);
      }

      // Gestion des 401 → tentative de refresh
      if (error.status === 401 && !isRefreshing) {
        isRefreshing = true;

        return auth.refresh().pipe( // ✅ ici on appelle refresh()
          switchMap((newToken) => {
            isRefreshing = false;

            if (newToken) {
              // ✅ Rejoue la requête initiale avec le nouveau token
              const retryReq = req.clone({ setHeaders: { Authorization: `Bearer ${auth.getToken()}` } });
              return next(retryReq);
            } else {
              // ❌ Refresh échoué → déconnexion
              auth.logout(); // ✅ ici on appelle logout()
              window.location.href = '/login';
              return throwError(() => error);
            }
          }),
          catchError(err => {
            isRefreshing = false;
            auth.logout(); // ✅ idem
            window.location.href = '/login';
            return throwError(() => err);
          })
        );
      }

      return throwError(() => error);
    })
  );
};
