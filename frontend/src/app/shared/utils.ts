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




import { EventInput } from '@fullcalendar/core';
import {ChauffeurCalendrierItem} from '../models/calendrier.model';


export type CalendarColors = {
  paye: string;
  conge: string;
  text: string;
};

export const DEFAULT_COLORS: CalendarColors = {
  paye: '#16a34a',  // vert
  conge: '#dc2626', // rouge
  text: '#ffffff',
};

/**
 * Transforme un item (un chauffeur/contrat) en événements FullCalendar.
 * - Paiements = vert, Congés = rouge
 * - allDay: true (dates au format 'YYYY-MM-DD' renvoyées par l'API)
 */
export function toCalendarEvents(
  item: ChauffeurCalendrierItem,
  colors: CalendarColors = DEFAULT_COLORS
): EventInput[] {
  const titleBase =
    `${item?.contrat?.prenom_chauffeur ?? ''} ${item?.contrat?.nom_chauffeur ?? ''}`.trim()
    || `Contrat #${item?.contrat?.id ?? ''}`;

  const paid: EventInput[] = (item?.paiements ?? []).map((iso) => ({
    title: `${titleBase} – Paiement`,
    start: iso,           // "YYYY-MM-DD"
    allDay: true,
    backgroundColor: colors.paye,
    borderColor: colors.paye,
    textColor: colors.text,
    extendedProps: {
      type: 'paiement',
      contratId: item?.contrat?.id,
      user_unique_id: item?.contrat?.user_unique_id,
      rawDate: iso,
    },
  }));

  const off: EventInput[] = (item?.conges ?? []).map((iso) => ({
    title: `${titleBase} – Congé`,
    start: iso,
    allDay: true,
    backgroundColor: colors.conge,
    borderColor: colors.conge,
    textColor: colors.text,
    extendedProps: {
      type: 'conge',
      contratId: item?.contrat?.id,
      user_unique_id: item?.contrat?.user_unique_id,
      rawDate: iso,
    },
  }));

  return [...paid, ...off];
}

/**
 * Transforme une liste d'items en un tableau d'événements FullCalendar.
 */
export function toCalendarEventsFromList(
  items: ChauffeurCalendrierItem[] | null | undefined,
  colors: CalendarColors = DEFAULT_COLORS
): EventInput[] {
  if (!items?.length) return [];
  return items.flatMap((it) => toCalendarEvents(it, colors));
}

/**
 * (Optionnel) Regroupe des événements par date ISO "YYYY-MM-DD".
 * Utile si tu veux calculer des totaux par jour, etc.
 */
export function groupEventsByDate(events: EventInput[]): Record<string, EventInput[]> {
  return events.reduce<Record<string, EventInput[]>>((acc, ev) => {
    const start = (ev.start as string) ?? '';
    if (!start) return acc;
    acc[start] = acc[start] || [];
    acc[start].push(ev);
    return acc;
  }, {});
}
