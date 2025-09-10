import {Component, computed, DestroyRef, effect, inject, OnInit, signal} from '@angular/core';
import {AddGarant} from "../../components/add-garant/add-garant";
import {GarantService} from "../../services/garant";
import {MatDialog} from "@angular/material/dialog";
import {FormsModule} from "@angular/forms";
import {Garant} from "../../models/garant.model";
import * as XLSX from 'xlsx';

@Component({
  selector: 'app-garant-list',
  imports: [
    FormsModule
  ],
  templateUrl: './garant-list.html',
  styleUrl: './garant-list.css'
})
export class GarantList implements OnInit {
  private readonly dialog = inject(MatDialog);
  readonly garantService = inject(GarantService)

  readonly garants = this.garantService.garants;
  readonly isLoadingGarant = this.garantService.isLoadingGarant;
  readonly errorGarant = this.garantService.errorGarant;

  // --- PAGINATION ---
  readonly pageSize = signal(25);
  readonly pageIndex = signal(0);

  readonly query = signal('');

  // filtrage (si pas besoin, remplace "filtered()" par "garants()" en dessous)
  readonly filtered = computed(() => {
    const normalizeStr = (s: unknown) =>
        String(s ?? '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/œ/g, 'oe')
            .replace(/æ/g, 'ae')
            .replace(/ß/g, 'ss')
            .replace(/[\u2019\u2018’]/g, "'")
            .toLowerCase()
            .replace(/[^a-z0-9]+/gi, ' ')
            .trim();
    const normalizePhone = (s: unknown) => String(s ?? '').replace(/\D+/g, '');
    const qRaw = this.query().trim();
    const q     = normalizeStr(qRaw);
    const qNums = normalizePhone(qRaw);
    if (!q && !qNums) return this.garants();
    return this.garants().filter(g => {
      const hay = normalizeStr(
          [g.nom, g.prenom, g.ville, g.quartier, g.profession].filter(Boolean).join(' ')
      );
      const tel = normalizePhone(g.tel);
      const textMatch = q ? hay.includes(q) : false;
      const phoneMatch = qNums ? tel.includes(qNums) : false;

      return textMatch || phoneMatch;
    });
  });


  readonly total       = computed(() => this.filtered().length);
  readonly totalPages  = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly pageStart   = computed(() => this.pageIndex() * this.pageSize());
  readonly pageEnd     = computed(() => Math.min(this.pageStart() + this.pageSize(), this.total()));
  readonly pagedGarants = computed(() => this.filtered().slice(this.pageStart(), this.pageEnd()));


  // helper pour avoir des numéros condensés: [1, '…', 8, 9, 10, '…', 42]
  readonly visiblePages = computed<(number | string)[]>(() => {
    const total = this.totalPages();
    const current = this.pageIndex(); // 0-based
    const last = total - 1;
    const around = 1; // nb de pages visibles autour de la courante
    const pages: (number | string)[] = [];

    const push = (p: number) => pages.push(p);
    const DOTS = '…';

    const addRange = (s: number, e: number) => { for (let i = s; i <= e; i++) push(i); };

    if (total <= 7) { addRange(0, last); return pages; }

    // toujours montrer 0 et last
    push(0);

    let start = Math.max(1, current - around);
    let end   = Math.min(last - 1, current + around);

    if (start > 1) pages.push(DOTS);
    addRange(start, end);
    if (end < last - 1) pages.push(DOTS);

    push(last);
    return pages;
  });

  ngOnInit() {
    this.garantService.fetchGarants()
  }

  isPage(val: number | string): val is number {
    return typeof val === 'number';
  }

  // actions pagination
  goToPage(i: number) {
    const clamped = Math.max(0, Math.min(i, this.totalPages() - 1));
    this.pageIndex.set(clamped);
  }
  prev() { this.goToPage(this.pageIndex() - 1); }
  next() { this.goToPage(this.pageIndex() + 1); }

  // openGarantDialog() {
  //   const ref = this.dialog.open(AddGarant, {
  //     width: '90vw',
  //     maxWidth: '750px',
  //     maxHeight: 'none',
  //     panelClass: 'garant_modal',
  //     disableClose: true,
  //   });
  //   ref.afterClosed().subscribe(result => {
  //     if (result) {
  //       this.garantService.fetchGarants();
  //     }
  //   });
  // }

  openGarantDialog() {
    const ref = this.dialog.open(AddGarant, {
      width: '90vw',
      maxWidth: '750px',
      maxHeight: 'none',
      panelClass: 'garant_modal',
      disableClose: true,
      data: { mode: 'create' }   // 👈 important
    });
    ref.afterClosed().subscribe(result => {
      if (result) {
        this.garantService.fetchGarants();
      }
    });
  }

  openGarantEditDialog(garant: Garant) {
    const ref = this.dialog.open(AddGarant, {
      width: '90vw',
      maxWidth: '750px',
      maxHeight: 'none',
      panelClass: 'garant_modal',
      disableClose: true,
      data: { mode: 'edit', id: garant.id, garant }
    });
    ref.afterClosed().subscribe(result => {
      if (result) {
        this.garantService.fetchGarants();
      }
    });
  }

  refresh(){
    this.garantService.fetchGarants();
  }





  // --- Helpers généraux ---
  private nowSlug(): string {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}-${pad(d.getMinutes())}`;
  }

  private mapGarantRow(g: Garant): (string | number)[] {
    return [
      g.id ?? '',
      g.nom ?? '',
      g.prenom ?? '',
      g.tel ?? '',
      g.ville ?? '',
      g.quartier ?? '',
      g.profession ?? ''
    ];
  }

// CSV safe: échappe ; , " retours-ligne, etc.
  private toCSV(rows: (string | number)[][], sep = ','): string {
    const esc = (v: string | number) => {
      const s = String(v ?? '');
      const needsQuotes = /["\r\n,;]/.test(s);
      const q = s.replace(/"/g, '""');
      return needsQuotes ? `"${q}"` : q;
    };
    return rows.map(r => r.map(esc).join(sep)).join('\r\n');
  }

  private download(content: BlobPart, filename: string, mime: string) {
    const blob = new Blob([content], { type: mime });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(a.href);
    a.remove();
  }

// --- Exports publics ---
  exportCSV(allFiltered: boolean = true) {
    const header = ['ID', 'Nom', 'Prénom', 'Téléphone', 'Ville', 'Quartier', 'Profession'];
    const data = (allFiltered ? this.filtered() : this.pagedGarants()).map(g => this.mapGarantRow(g));
    const csv = this.toCSV([header, ...data], ','); // utilise ',' ; mets ';' si tu préfères
    this.download(csv, `garants_${this.nowSlug()}.csv`, 'text/csv;charset=utf-8;');
  }


  exportExcel(allFiltered: boolean = true) {
    const list = (allFiltered ? this.filtered() : this.pagedGarants()).map(g => ({
      ID: g.id ?? '',
      Nom: g.nom ?? '',
      Prénom: g.prenom ?? '',
      Téléphone: g.tel ?? '',
      Ville: g.ville ?? '',
      Quartier: g.quartier ?? '',
      Profession: g.profession ?? ''
    }));

    const ws = XLSX.utils.json_to_sheet(list, { skipHeader: false });
    // Ajuste un peu la largeur des colonnes (optionnel)
    ws['!cols'] = [
      { wch: 6 },  // ID
      { wch: 20 }, // Nom
      { wch: 20 }, // Prénom
      { wch: 14 }, // Téléphone
      { wch: 16 }, // Ville
      { wch: 16 }, // Quartier
      { wch: 20 }  // Profession
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Garants');
    XLSX.writeFile(wb, `garants_${this.nowSlug()}.xlsx`);
  }


}
