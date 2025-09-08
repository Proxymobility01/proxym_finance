import {Component, inject, OnInit, signal, computed, effect} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {DatePipe, LowerCasePipe} from '@angular/common';
import {HighlightPipe} from '../../shared/highlight-pipe';
import {NumberPipe} from '../../shared/number-pipe';
import * as XLSX from 'xlsx';
import {ContratBatterieService} from "../../services/contrat-batterie";
import {MatDialog} from "@angular/material/dialog";
import {AddContratChauffeur} from "../../components/add-contrat-chauffeur/add-contrat-chauffeur";
import {AddContratBatterie} from "../../components/add-contrat-batterie/add-contrat-batterie";

type StatusFilter = '' | 'termine' | 'encours' | 'suspendu';
type DateFilterMode = 'today' | 'week' | 'month' | 'year' | 'specific' | 'range' | 'all';
type PageItem = { type: 'page', index: number } | { type: 'dots' };

@Component({
  selector: 'app-contrat-batterie-list',
  standalone: true,
  imports: [FormsModule, DatePipe, NumberPipe, HighlightPipe, LowerCasePipe],
  templateUrl: './contrat-batterie-list.html',
  styleUrl: './contrat-batterie-list.css'
})
export class ContratBatterieList implements OnInit {
  private readonly contratBattService = inject(ContratBatterieService);
  private readonly dialog = inject(MatDialog);

  readonly query = signal<string>('');
  readonly status = signal<StatusFilter>('');
  readonly dateMode = signal<DateFilterMode>('all');
  readonly dateSpecific = signal<string>('');
  readonly dateStart = signal<string>('');
  readonly dateEnd = signal<string>('');

  readonly contratsBatt = this.contratBattService.contratsBatt;
  readonly isLoadingContrat = this.contratBattService.isLoadingContratBatt;
  readonly errorContrat = this.contratBattService.errorContratBatt;

  ngOnInit() {
    this.contratBattService.fetchContratBatterie();
  }

  // --- Helpers (normalisation & dates) ---
  private normalizeStr(s: unknown): string {
    return String(s ?? '')
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().trim();
  }
  private parseDate(d: unknown): Date | null {
    if (!d) return null;
    const dt = new Date(String(d));
    return isNaN(+dt) ? null : new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
  }
  private startOfDay(d: Date){ return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  private endOfDay(d: Date){ return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23,59,59,999); }
  private getPeriodRange(mode: DateFilterMode, specific: string, start: string, end: string) {
    const today = this.startOfDay(new Date());
    if (mode === 'today') return { from: today, to: this.endOfDay(today) };
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
    return {};
  }

  // --- Filtrage ---
  readonly filteredContrats = computed(() => {
    const list = this.contratBattService.contratsBatt();
    if (!list?.length) return [];

    const q = this.normalizeStr(this.query());
    const { from, to } = this.getPeriodRange(this.dateMode(), this.dateSpecific(), this.dateStart(), this.dateEnd());
    const st = this.status();

    return list.filter(c => {
      // recherche
      let okSearch = true;
      if (q) {
        okSearch = this.normalizeStr(c.reference).includes(q)
            || this.normalizeStr(c.proprietaire).includes(q);
      }
      // statut
      let okStatus = true;
      if (st) okStatus = this.normalizeStr(c.statut_contrat) === st;
      // date
      let okDate = true;
      if (from || to) {
        const d = this.parseDate(c.date_signature);
        okDate = d ? (!from || d >= from) && (!to || d <= to) : false;
      }
      return okSearch && okStatus && okDate;
    });
  });

  // --- Pagination ---
  readonly pageSize  = signal(25);
  readonly pageIndex = signal(0);
  readonly total      = computed(() => this.filteredContrats().length);
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly pageStart  = computed(() => this.pageIndex() * this.pageSize());
  readonly pageEnd    = computed(() => Math.min(this.pageStart() + this.pageSize(), this.total()));
  readonly pagedContrats = computed(() =>
      this.filteredContrats().slice(this.pageStart(), this.pageEnd())
  );

  private _keepPageInRange = effect(() => {
    if (this.pageIndex() > this.totalPages() - 1) this.pageIndex.set(0);
  });

  readonly visiblePages = computed<PageItem[]>(() => {
    const total = this.totalPages();
    const current = this.pageIndex();
    const last = total - 1;
    const out: PageItem[] = [];
    const addRange = (s: number, e: number) => { for (let i = s; i <= e; i++) out.push({ type: 'page', index: i }); };

    if (total <= 7) { addRange(0, last); return out; }

    out.push({ type: 'page', index: 0 });
    let s = Math.max(1, current - 1);
    let e = Math.min(last - 1, current + 1);
    if (s > 1) out.push({ type: 'dots' });
    addRange(s, e);
    if (e < last - 1) out.push({ type: 'dots' });
    out.push({ type: 'page', index: last });
    return out;
  });

  goToPage(i: number) { this.pageIndex.set(Math.max(0, Math.min(i, this.totalPages() - 1))); }
  prev() { this.goToPage(this.pageIndex() - 1); }
  next() { this.goToPage(this.pageIndex() + 1); }
  changePageSize(size: number) { this.pageSize.set(size); this.pageIndex.set(0); }

  // --- Exports ---
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
  private mapRow(c: any) {
    return {
      Référence: c.reference ?? '',
      Propriétaire: c.proprietaire ?? '',
      'Date signature': c.date_signature ? new Date(c.date_signature).toLocaleDateString('fr-FR') : '',
      'Montant payé (FCFA)': c.montant_paye ?? '',
      'Montant restant (FCFA)': c.montant_restant ?? '',
      'Montant total (FCFA)': c.montant_total ?? '',
      'Montant caution (FCFA)': c.montant_caution ?? '',
      'Statut': c.statut_contrat ?? ''
    };
  }
  private toCSV(rows: Record<string, any>[], sep = ','): string {
    if (!rows.length) return '';
    const headers = Object.keys(rows[0]);
    const esc = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    return headers.join(sep) + '\r\n' + rows.map(r => headers.map(h => esc(r[h])).join(sep)).join('\r\n');
  }
  exportCSV(allFiltered: boolean = true) {
    const list = (allFiltered ? this.filteredContrats() : this.pagedContrats()).map(c => this.mapRow(c));
    const csv = this.toCSV(list, ',');
    this.download(csv, `contrats_batterie_${this.nowSlug()}.csv`, 'text/csv;charset=utf-8;');
  }
  exportExcel(allFiltered: boolean = true) {
    const list = (allFiltered ? this.filteredContrats() : this.pagedContrats()).map(c => this.mapRow(c));
    const ws = XLSX.utils.json_to_sheet(list);
    ws['!cols'] = [
      { wch: 16 }, { wch: 20 }, { wch: 14 },
      { wch: 18 }, { wch: 20 }, { wch: 18 },
      { wch: 20 }, { wch: 12 }
    ];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Contrats');
    XLSX.writeFile(wb, `contrats_batterie_${this.nowSlug()}.xlsx`);
  }

  openContratBatterieDialog() {
    const dialogRef = this.dialog.open(AddContratBatterie, {
      width: '90vw',
      maxWidth: '700px',
      maxHeight: 'none',
      panelClass: 'contrat_batterie',
      disableClose: true,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        // result contient le payload renvoyé par la modal
        console.log('Contrat créé :', result);

        // 👉 ici tu peux rafraîchir ta liste ou rappeler ton service backend
        // this.contratCService.fetchAll();
      }
    });
  }


}
