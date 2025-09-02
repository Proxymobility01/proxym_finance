import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'noGroupNumber', standalone: true })
export class NumberPipe implements PipeTransform {
  transform(value: number | string | null | undefined): string {
    if (value === null || value === undefined) return '0';
    const num = typeof value === 'string' ? Number(value) : value;
    if (Number.isNaN(num)) return '0';
    // Pas de séparateurs, 0 décimales
    return new Intl.NumberFormat('fr-FR', {
      useGrouping: false,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  }
}
