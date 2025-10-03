// auth.guard.ts
import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import {AuthService} from './auth';


export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);


  if (!auth.isLoggedIn()) {
    router.navigate(['/login']);
    return false;
  }


  const expectedRole = route.data['role'] as string | undefined;
  const actualRole = auth.role();

  if (expectedRole && actualRole !== expectedRole) {
    const fallback = getFallbackRoute(actualRole);
    router.navigate([fallback]);
    return false;
  }

  return true;
};

function getFallbackRoute(role: string | null): string {
  switch ((role ?? '').toLowerCase()) {
    case 'gestionnairefinancier':
      return 'contrat/chauffeur';
    case 'administrateur':
      return '#';
    default:
      return '/';
  }
}
