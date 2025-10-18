import {AbstractControl, ValidationErrors} from '@angular/forms';
import {CONTRACT_VALIDATION} from '../models/contrat-chauffeur.model';

export function dateCoherenceValidator(group: AbstractControl): ValidationErrors | null {
  const sig = group.get('date_signature')?.value;
  const deb = group.get('date_debut')?.value;
  if (!sig || !deb) return null;
  if (!CONTRACT_VALIDATION.DATE_PATTERN.test(sig) || !CONTRACT_VALIDATION.DATE_PATTERN.test(deb)) return null;
  return new Date(deb).getTime() < new Date(sig).getTime() ? { dateOrder: true } : null;
}

export function engagedNotAboveTotalValidator(group: AbstractControl): ValidationErrors | null {
  const total = (group.get('montant_total')?.value ?? '').toString();
  const engage = (group.get('montant_engage')?.value ?? '').toString();
  const re = CONTRACT_VALIDATION.MONEY_STRING_PATTERN;
  if (!re.test(total) || !re.test(engage)) return null;
  const n = (s: string) => Number(s.replace(/\s/g, ''));
  return n(engage) > n(total) ? { engageAboveTotal: true } : null;
}

export function normalizeMoneyString(v: any): string {
  return (v ?? '').toString().trim().replace(/\s/g, '');
}
export function normalizeFileToken(v: any): string {
  return (v ?? '').toString().trim();
}


export function norm(v: any): string { return (v ?? '').toString().trim(); }


