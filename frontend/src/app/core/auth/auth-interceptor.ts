// src/app/auth/auth.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth';

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

  let clonedReq = req;

  // ✅ Ajoute Authorization sauf pour les routes d’auth
  if (token && !shouldSkip) {
    const isFormData = req.body instanceof FormData;

    // ✅ Si c’est un FormData → ne pas forcer Content-Type
    if (isFormData) {
      clonedReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        },
        headers: req.headers.delete('Content-Type') // 🔥 important
      });
    } else {
      clonedReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
    }
  }

  return next(clonedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (shouldSkip) {
        return throwError(() => error);
      }

      // Gestion automatique du refresh token
      if (error.status === 401 && !isRefreshing) {
        isRefreshing = true;

        return auth.refresh().pipe(
          switchMap((newToken) => {
            isRefreshing = false;

            if (newToken) {
              const retryReq = clonedReq.clone({
                setHeaders: { Authorization: `Bearer ${auth.getToken()}` }
              });
              return next(retryReq);
            } else {
              auth.logout();
              window.location.href = '/login';
              return throwError(() => error);
            }
          }),
          catchError(err => {
            isRefreshing = false;
            auth.logout();
            window.location.href = '/login';
            return throwError(() => err);
          })
        );
      }

      return throwError(() => error);
    })
  );
};
