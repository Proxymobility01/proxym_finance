import {Component, inject, OnInit, signal, computed, effect} from '@angular/core';

import { FormsModule } from '@angular/forms';
import {DatePipe, LowerCasePipe} from '@angular/common';
import {NumberPipe} from '../../shared/number-pipe';
import {MatDialog} from "@angular/material/dialog";
import { ContratChauffeurService} from "../../services/contrat-chauffeur";
import {AddContratChauffeur} from "../../components/add-contrat-chauffeur/add-contrat-chauffeur";
import {HighlightPipe} from "../../shared/highlight-pipe";
import * as XLSX from 'xlsx';
import {ContratChauffeur} from '../../models/contrat-chauffeur.model';
import {ChangerStatutContrat} from '../../components/changer-statut-contrat/changer-statut-contrat';
import {MatSnackBar} from '@angular/material/snack-bar';


type StatusFilter = '' | 'termine' | 'encours' | 'suspendu' | 'annule';
type DateFilterMode = 'today' | 'week' | 'month' | 'year' | 'specific' | 'range' | 'all';
type PageItem = { type: 'page', index: number } | { type: 'dots' };

@Component({
  selector: 'app-contrat-chauffeur-list',
  standalone: true,
  imports: [
    FormsModule,
    DatePipe,
    NumberPipe,
    HighlightPipe,
    LowerCasePipe
  ],
  templateUrl: './contrat-chauffeur-list.html',
  styleUrl: './contrat-chauffeur-list.css'
})
export class ContratChauffeurList implements OnInit {

  private readonly dialog = inject(MatDialog);
  private readonly contratChService = inject(ContratChauffeurService);
  private readonly snackBar = inject(MatSnackBar);

  readonly query       = signal<string>('');
  readonly status      = signal<StatusFilter>('');
  readonly dateMode    = signal<DateFilterMode>('all');
  readonly dateSpecific= signal<string>('');
  readonly dateStart   = signal<string>('');
  readonly dateEnd     = signal<string>('');

  readonly contratsCh = this.contratChService.contratsCh;
  readonly isLoadingContrat = this.contratChService.isLoadingContrat;
  readonly errorContrat = this.contratChService.errorContrat;

  ngOnInit() {
    this.contratChService.fetchContratChauffeur()
  }

  refresh() {
    this.contratChService.fetchContratChauffeur()
  }

  openChangeStatutDialog(c: ContratChauffeur) {
    this.dialog.open(ChangerStatutContrat, {
      width: '400px',
      data: { id: c.id, currentStatut: c.statut, chauffeur: c.chauffeur },
      disableClose: true
    }).afterClosed().subscribe(res => {
      if (res?.success) {
        this.snackBar.open(
          'Statut du contrat mis à jour ✅',
          'Ok',
          {duration: 3000}
        );
        this.contratChService.fetchContratChauffeur();
      }
    });
  }


  openContratChauffeurDialog() {
    const dialogRef = this.dialog.open(AddContratChauffeur, {
      width: '90vw',
      maxWidth: '800px',
      maxHeight: 'none',
      panelClass: 'contrat_chauffeur',
      disableClose: true,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) this.refresh();
    });
  }



  // helpers normalisation + dates
  private normalizeStr(s: unknown): string {
    return String(s ?? '')
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/œ/g,'oe').replace(/æ/g,'ae').replace(/ß/g,'ss')
        .replace(/[\u2019\u2018’]/g, "'")
        .toLowerCase().trim();
  }
  private parseDate(d: unknown): Date | null {
    if (!d) return null;
    const s = String(d);
    // laisse Date parser ISO/aaaa-mm-jj; fallback split
    const dt = new Date(s);
    if (!isNaN(+dt)) return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
    const m = s.match(/^(\d{4})[-/](\d{2})[-/](\d{2})$/);
    if (m) return new Date(+m[1], +m[2]-1, +m[3]);
    return null;
  }
  private startOfDay(d: Date){ return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  private endOfDay(d: Date){ return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23,59,59,999); }
  private getPeriodRange(mode: DateFilterMode, specific: string, start: string, end: string): {from?: Date, to?: Date} {
    const today = this.startOfDay(new Date());
    if (mode === 'today') return { from: today, to: this.endOfDay(today) };
    if (mode === 'week') {
      const day = today.getDay();            // 0=Dim
      const diffToMon = (day === 0 ? -6 : 1 - day);
      const from = new Date(today); from.setDate(today.getDate() + diffToMon);
      const to = new Date(from); to.setDate(from.getDate() + 6); return { from, to: this.endOfDay(to) };
    }
    if (mode === 'month') {
      const from = new Date(today.getFullYear(), today.getMonth(), 1);
      const to = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      return { from, to: this.endOfDay(to) };
    }
    if (mode === 'year') {
      const from = new Date(today.getFullYear(), 0, 1);
      const to = new Date(today.getFullYear(), 11, 31);
      return { from, to: this.endOfDay(to) };
    }
    if (mode === 'specific') {
      const d = this.parseDate(specific);
      return d ? { from: d, to: this.endOfDay(d) } : {};
    }
    if (mode === 'range') {
      const ds = this.parseDate(start);
      const de = this.parseDate(end);
      if (ds && de) return { from: ds, to: this.endOfDay(de) };
      if (ds && !de) return { from: ds };
      if (!ds && de) return { to: this.endOfDay(de) };
      return {};
    }
    return {}; // 'all'
  }

// --- Liste filtrée ---
  readonly filteredContrats = computed(() => {
    const list = this.contratChService.contratsCh(); // source
    if (!list?.length) return [];

    const q = this.normalizeStr(this.query());
    const mode = this.dateMode();
    const { from, to } = this.getPeriodRange(mode, this.dateSpecific(), this.dateStart(), this.dateEnd());
    const st = this.status();

    return list.filter(c => {
      // Recherche
      let okSearch = true;
      if (q) {
        const ref = this.normalizeStr(c?.reference_contrat);
        const nom = this.normalizeStr(c?.chauffeur);
        okSearch = ref.includes(q) || nom.includes(q);
      }

      // Statut (robuste: booléen ou string)
      let okStatus = true;
      if (st) {
        const valBool   = (typeof c?.statut === 'boolean') ? c.statut : undefined;
        const valString = this.normalizeStr(c?.statut ?? c?.statut);

        if (st === 'termine')  okStatus = (valBool === true) || valString === 'termine';
        if (st === 'encours')  okStatus = (valBool === false) || valString === 'en cours' || valString === 'encours';
        if (st === 'suspendu') okStatus = valString === 'suspendu';
      }

      // Période
      let okDate = true;
      if (from || to) {
        const d = this.parseDate(c?.date_signature);
        if (!d) okDate = false;
        else {
          okDate = (!from || d >= from) && (!to || d <= to);
        }
      }

      return okSearch && okStatus && okDate;
    });
  });

// total filtré (utile pour le footer)
  readonly filteredTotal = computed(() => this.filteredContrats().length);

  readonly pageSize  = signal(25);
  readonly pageIndex = signal(0); // 0-based

  readonly total      = computed(() => this.filteredContrats().length);
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly pageStart  = computed(() => this.pageIndex() * this.pageSize());
  readonly pageEnd    = computed(() => Math.min(this.pageStart() + this.pageSize(), this.total()));
  readonly pagedContrats = computed(() =>
      this.filteredContrats().slice(this.pageStart(), this.pageEnd())
  );

// conserve la page dans les bornes quand les filtres changent
  private _keepPageInRange = effect(() => {
    const pages = this.totalPages();
    if (this.pageIndex() > pages - 1) this.pageIndex.set(0);
  });

// Pagination condensée : 1 … 8 9 10 … 42

  readonly visiblePages = computed<PageItem[]>(() => {
    const total = this.totalPages();
    const current = this.pageIndex();
    const last = total - 1;
    const around = 1;
    const out: PageItem[] = [];
    const addRange = (s: number, e: number) => { for (let i = s; i <= e; i++) out.push({ type: 'page', index: i }); };

    if (total <= 7) { addRange(0, last); return out; }

    out.push({ type: 'page', index: 0 });
    let s = Math.max(1, current - around);
    let e = Math.min(last - 1, current + around);
    if (s > 1) out.push({ type: 'dots' });
    addRange(s, e);
    if (e < last - 1) out.push({ type: 'dots' });
    out.push({ type: 'page', index: last });
    return out;
  });

// Actions
  goToPage(i: number) {
    const clamped = Math.max(0, Math.min(i, this.totalPages() - 1));
    this.pageIndex.set(clamped);
  }
  prev() { this.goToPage(this.pageIndex() - 1); }
  next() { this.goToPage(this.pageIndex() + 1); }
  changePageSize(size: number) { this.pageSize.set(size); this.pageIndex.set(0); }




// =======================
// EXPORTS CSV / EXCEL
// =======================

// Helpers export
  private nowSlug(): string {
    const d = new Date(); const pad = (n: number) => String(n).padStart(2,'0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}-${pad(d.getMinutes())}`;
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

// Map ligne pour export
  private mapRow(c: any) {
    const statut =
        (typeof c?.status === 'boolean')
            ? (c.status ? 'Terminé' : 'En cours')
            : (String(c?.status ?? c?.status_str ?? '').toLowerCase());

    // format date en JJ/MM/AAAA si possible
    let dateStr = '';
    try {
      const d = c?.date_signature ? new Date(c.date_signature) : null;
      if (d && !isNaN(+d)) dateStr = d.toLocaleDateString('fr-FR');
    } catch {}

    return {
      Référence: c?.reference ?? '',
      Chauffeur: c?.nom_chauffeur ?? '',
      'Date signature': dateStr,
      'Montant payé (FCFA)': c?.montant_paye ?? '',
      'Montant restant (FCFA)': c?.montant_restant ?? '',
      'Montant total (FCFA)': c?.montant_total ?? '',
      Statut: statut
    };
  }

// ------- CSV (sans dépendance) -------
  private toCSV(rows: Record<string, any>[], sep = ','): string {
    if (!rows.length) return '';
    const headers = Object.keys(rows[0]);
    const esc = (v: any) => {
      const s = String(v ?? '');
      const needs = /["\r\n,;]/.test(s);
      const q = s.replace(/"/g, '""');
      return needs ? `"${q}"` : q;
    };
    const head = headers.map(esc).join(sep);
    const body = rows.map(r => headers.map(h => esc(r[h])).join(sep)).join('\r\n');
    return head + '\r\n' + body;
  }

// Exporte la liste filtrée (par défaut). Passe false pour n’exporter que la page courante.
  exportCSV(allFiltered: boolean = true) {
    const list = (allFiltered ? this.filteredContrats() : this.pagedContrats()).map(c => this.mapRow(c));
    const csv = this.toCSV(list, ','); // mets ';' si Excel FR
    this.download(csv, `contrats_chauffeur_${this.nowSlug()}.csv`, 'text/csv;charset=utf-8;');
  }

// ------- Excel (.xlsx) avec SheetJS -------
   // <-- mets cet import en haut du fichier

  exportExcel(allFiltered: boolean = true) {
    const list = (allFiltered ? this.filteredContrats() : this.pagedContrats()).map(c => this.mapRow(c));
    const ws = XLSX.utils.json_to_sheet(list, { skipHeader: false });
    ws['!cols'] = [
      { wch: 16 }, // Référence
      { wch: 22 }, // Chauffeur
      { wch: 14 }, // Date
      { wch: 18 }, // Payé
      { wch: 20 }, // Restant
      { wch: 18 }, // Total
      { wch: 12 }  // Statut
    ];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Contrats');
    XLSX.writeFile(wb, `contrats_chauffeur_${this.nowSlug()}.xlsx`);
  }
}
