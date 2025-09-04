import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  standalone: true,
  name: 'highlight'
})
export class HighlightPipe implements PipeTransform {

  transform(text: string | null | undefined, search?: string | null): string {
    if (!text) return '';
    if (!search || !search.trim()) return this.escapeHtml(text);

    // Découper en termes (exclut les mots d'1 char pour éviter le bruit)
    const terms = search
      .trim()
      .split(/\s+/)
      .filter(w => w.length > 1);

    if (terms.length === 0) return this.escapeHtml(text);

    // Construire une version "sans accents" du texte + carte d’index vers l’original
    const { norm, map } = this.buildNormalizedWithMap(text);

    // Récupérer toutes les occurrences (insensible à la casse) dans la version normalisée
    const ranges: Array<[number, number]> = [];
    for (const t of terms) {
      const escaped = t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // échappe regex
      const re = new RegExp(escaped.normalize('NFD').replace(/[\u0300-\u036f]/g, ''), 'gi');

      let m: RegExpExecArray | null;
      while ((m = re.exec(norm)) !== null) {
        const startN = m.index;
        const endN = m.index + m[0].length;
        // Convertir indices normalisés -> indices dans le texte original
        const startO = map[startN];
        const endO = (endN - 1 < map.length) ? map[endN - 1] + 1 : text.length;
        ranges.push([startO, endO]);
        // éviter boucles infinies sur matches vides
        if (m.index === re.lastIndex) re.lastIndex++;
      }
    }

    if (ranges.length === 0) return this.escapeHtml(text);

    // Fusionner les plages qui se chevauchent
    ranges.sort((a, b) => a[0] - b[0]);
    const merged: Array<[number, number]> = [];
    for (const r of ranges) {
      if (!merged.length || r[0] > merged[merged.length - 1][1]) {
        merged.push(r);
      } else {
        merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], r[1]);
      }
    }

    // Reconstruire le texte avec <mark>
    let out = '';
    let cursor = 0;
    for (const [s, e] of merged) {
      if (s > cursor) out += this.escapeHtml(text.slice(cursor, s));
      out += `<mark>${this.escapeHtml(text.slice(s, e))}</mark>`;
      cursor = e;
    }
    if (cursor < text.length) out += this.escapeHtml(text.slice(cursor));

    return out;
  }

  /** Construit une chaîne normalisée (sans accents) et une map d’index -> index original */
  private buildNormalizedWithMap(src: string) {
    const normChars: string[] = [];
    const map: number[] = [];
    // itérer par points de code (gère emojis/accents)
    const orig = Array.from(src);
    for (let i = 0; i < orig.length; i++) {
      const base = orig[i].normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      for (let j = 0; j < base.length; j++) {
        normChars.push(base[j]);
        map.push(i);
      }
    }
    return { norm: normChars.join(''), map };
  }

  /** Sécurise le HTML en échappant les caractères spéciaux (Angular conservera <mark>) */
  private escapeHtml(s: string): string {
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

}
