// src/app/core/api-config.token.ts
import { InjectionToken } from '@angular/core';

export interface ApiConfig { apiUrl: string; wsUrl: string; }
export const AUTH_API_CONFIG = new InjectionToken<ApiConfig>('AUTH_API_CONFIG');
export const API_CONFIG = new InjectionToken<ApiConfig>('API_CONFIG');
