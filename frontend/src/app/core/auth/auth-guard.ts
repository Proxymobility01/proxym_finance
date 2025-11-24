import { CanActivateFn, Router, UrlTree } from '@angular/router';
import { inject } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { Observable } from 'rxjs';
import { map, filter, take } from 'rxjs/operators';
import {AuthService} from './auth';

/**
 * Ce garde est asynchrone. Il attend que le AuthService ait fini
 * de tenter la connexion initiale (via initAuth) avant de prendre une décision.
 */
export const authGuard: CanActivateFn = (route, state): Observable<boolean | UrlTree> => {
  const auth = inject(AuthService);
  const router = inject(Router);

  // 1. On s'abonne au signal 'authReady'
  return toObservable(auth.authReady).pipe(

    // 2. On attend que le signal devienne 'true'
    filter(ready => ready),

    // 3. On prend la première valeur 'true' et on se désabonne
    take(1),

    // 4. L'état d'authentification est maintenant connu, on peut exécuter les vérifications
    map(() => {

      // 5. L'utilisateur est-il connecté ?
      if (!auth.isLoggedIn()) {
        // Non. On redirige vers /login
        return router.createUrlTree(['/login']);
      }

      // 6. L'utilisateur EST connecté. On vérifie les rôles.
      const expectedRole = route.data['role'] as string | undefined;
      const actualRole = auth.role(); // Vient du signal currentUser (profil local)

      if (expectedRole && actualRole !== expectedRole) {
        // Mauvais rôle, redirection vers la page par défaut de ce rôle
        const fallback = getFallbackRoute(actualRole);
        return router.createUrlTree([fallback]);
      }

      // 7. L'utilisateur est connecté et a le bon rôle (ou pas de rôle requis)
      return true;
    })
  );
};

/**
 * Cette fonction est correcte et n'a pas besoin de changer.
 * Elle utilise le 'role' du profil local.
 */
function getFallbackRoute(role: string | null): string {
  switch ((role ?? '').toLowerCase()) {
    case 'gestionnairefinancier':
      return 'contrat/chauffeur';
    case 'administrateur':
      return '#'; // Vous voudrez peut-être changer ceci pour un vrai tableau de bord admin
    default:
      return '/'; // Page d'accueil par défaut
  }
}
