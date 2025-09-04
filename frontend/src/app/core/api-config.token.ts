// src/app/core/api-config.token.ts
import { InjectionToken } from '@angular/core';

export interface ApiConfig { apiUrl: string; wsUrl: string; }
export const API_CONFIG = new InjectionToken<ApiConfig>('API_CONFIG');
