

import { HttpInterceptorFn, HttpErrorResponse, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, filter, switchMap, take, throwError, BehaviorSubject } from 'rxjs';
import {AuthService} from './auth';


// --- Variables d'état (en dehors de la fonction pour persister entre les appels) ---
let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<string | null>(null);

// URLs à ignorer (Auth + Refresh)
const AUTH_URLS_SKIP = [
  '/auth/token/',
  '/auth/token/refresh/',
  '/auth/logout/'
];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const shouldSkip = AUTH_URLS_SKIP.some(u => req.url.includes(u));

  // Fonction helper pour ajouter le header
  const addToken = (request: HttpRequest<any>, token: string | null) => {
    if (token) {
      return request.clone({
        setHeaders: { Authorization: `Bearer ${token}` }
      });
    }
    return request;
  };

  // 1. Ajouter le token actuel s'il existe
  let clonedReq = req;
  const token = auth.getToken();
  if (token && !shouldSkip) {
    clonedReq = addToken(req, token);
  }

  return next(clonedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Si c'est une requête d'auth qui échoue, on laisse passer l'erreur (évite boucle infinie)
      if (shouldSkip) {
        return throwError(() => error);
      }

      // Gestion de l'erreur 401 (Token expiré)
      if (error.status === 401) {

        // CAS A : Nous sommes le PREMIER à détecter l'expiration -> On lance le refresh
        if (!isRefreshing) {
          isRefreshing = true;
          refreshTokenSubject.next(null); // On bloque les autres requêtes

          return auth.refresh().pipe(
            switchMap((res) => {
              isRefreshing = false;
              // On notifie les autres requêtes en attente avec le nouveau token
              refreshTokenSubject.next(res.access);
              return next(addToken(req, res.access));
            }),
            catchError((err) => {
              isRefreshing = false;
              auth.logout(); // Si le refresh échoue, on déconnecte tout le monde
              return throwError(() => err);
            })
          );
        }

        // CAS B : Un refresh est DÉJÀ en cours -> On attend
        else {
          return refreshTokenSubject.pipe(
            filter(token => token !== null), // On attend que la valeur ne soit plus null
            take(1), // On ne prend que la première valeur valide et on se désabonne
            switchMap(token => {
              // Le token est arrivé ! On rejoue la requête initiale
              return next(addToken(req, token));
            })
          );
        }
      }

      // Autres erreurs (403, 500...) -> On laisse passer
      return throwError(() => error);
    })
  );
};
