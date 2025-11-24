import {
  APP_INITIALIZER,
  ApplicationConfig,
  importProvidersFrom, inject, LOCALE_ID, provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZoneChangeDetection
} from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import {provideHttpClient, withInterceptors} from '@angular/common/http';
import {authInterceptor} from './core/auth/auth-interceptor';
import {API_CONFIG, AUTH_API_CONFIG} from './core/api-config.token';
import {environment} from '../environments/environment';
import { MatSnackBarModule} from '@angular/material/snack-bar';
import { registerLocaleData } from '@angular/common';
import localeFr from '@angular/common/locales/fr';
import { MAT_DATE_LOCALE } from '@angular/material/core';
import {AuthService} from './core/auth/auth';

registerLocaleData(localeFr);


export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    importProvidersFrom(MatSnackBarModule),
    { provide: LOCALE_ID, useValue: 'fr-FR' },
    { provide: MAT_DATE_LOCALE, useValue: 'fr-FR' },
    { provide: API_CONFIG, useValue: { apiUrl: environment.API_URL } },
    { provide: AUTH_API_CONFIG, useValue: { apiUrl: environment.AUTH_API_CONFIG } },
    provideAppInitializer(() => {
      const authService = inject(AuthService);
      return authService.initAuth();
    }),

  ]
};
