import { Component, OnInit, inject, signal, computed, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {DatePipe, DecimalPipe, NgClass} from '@angular/common';
import * as XLSX from 'xlsx';

import { Penalite, StatutPenalite } from '../../models/penalite.model';
import { HighlightPipe } from '../../shared/highlight-pipe';
import { PenaliteService } from '../../services/penalite';
import {NumberPipe} from '../../shared/number-pipe';
import {AddPaiementPenalite} from '../../components/add-paiement-penalite/add-paiement-penalite';
import {MatDialog} from '@angular/material/dialog';

type StatutFilter = '' | StatutPenalite;
type DateFilterMode = 'today' | 'week' | 'month' | 'year' | 'specific' | 'range' | 'all';
type PageItem = { type: 'page'; index: number } | { type: 'dots' };

@Component({
  selector: 'app-penalite-list',
  imports: [
    HighlightPipe,
    DatePipe,
        FormsModule,
    NumberPipe
  ],
  templateUrl: './penalite-list.html',
  styleUrl: './penalite-list.css'
})
export class PenaliteList implements OnInit{
  private readonly penaliteService = inject(PenaliteService);
  private dialog = inject(MatDialog)

  // ---------- Filtres ----------
  readonly query        = signal<string>('');             // chauffeur ou référence
  readonly statut       = signal<StatutFilter>('');       // non_paye | partiellement_paye | paye
  readonly dateMode     = signal<DateFilterMode>('all');  // sur date_paiement_manquee
  readonly dateSpecific = signal<string>('');             // YYYY-MM-DD
  readonly dateStart    = signal<string>('');             // YYYY-MM-DD
  readonly dateEnd      = signal<string>('');             // YYYY-MM-DD

  // ---------- Source ----------
  readonly penalites = this.penaliteService.penalites;
  readonly isLoading = this.penaliteService.isLoadingPenalite;
  readonly error     = this.penaliteService.errorPenalite;

  // ... dans la classe PenaliteList
  readonly statutLabel: Record<'non_paye'|'paye'|'partiellement_paye'|string, string> = {
    non_paye: 'Non payé',
    paye: 'Payé',
    partiellement_paye: 'Partiellement payé',
  };


  ngOnInit() {
    this.penaliteService.fetchPenalites();
  }

  // ---------- Helpers ----------
  private normalize(s: unknown): string {
    return String(s ?? '')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/œ/g, 'oe').replace(/æ/g, 'ae').replace(/ß/g, 'ss')
      .replace(/[\u2019\u2018’]/g, "'")
      .toLowerCase()
      .trim();
  }

  private parseISO(d: unknown): Date | null {
    if (!d) return null;
    const dt = new Date(String(d));
    if (!isNaN(+dt)) return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
    return null;
  }
  private startOfDay(d: Date) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  private endOfDay(d: Date)   { return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23,59,59,999); }

  private getPeriod(mode: DateFilterMode, specific: string, start: string, end: string): { from?: Date; to?: Date } {
    const today = this.startOfDay(new Date());

    if (mode === 'today') return { from: today, to: this.endOfDay(today) };

    if (mode === 'week') {
      const day = today.getDay(); // 0 = Dim
      const diffToMon = (day === 0 ? -6 : 1 - day);
      const from = new Date(today); from.setDate(today.getDate() + diffToMon);
      const to = new Date(from);    to.setDate(from.getDate() + 6);
      return { from, to: this.endOfDay(to) };
    }

    if (mode === 'month') {
      const from = new Date(today.getFullYear(), today.getMonth(), 1);
      const to   = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      return { from, to: this.endOfDay(to) };
    }

    if (mode === 'year') {
      const from = new Date(today.getFullYear(), 0, 1);
      const to   = new Date(today.getFullYear(), 11, 31);
      return { from, to: this.endOfDay(to) };
    }

    if (mode === 'specific') {
      const d = this.parseISO(specific);
      return d ? { from: d, to: this.endOfDay(d) } : {};
    }

    if (mode === 'range') {
      const ds = this.parseISO(start);
      const de = this.parseISO(end);
      if (ds && de)   return { from: ds, to: this.endOfDay(de) };
      if (ds && !de)  return { from: ds };
      if (!ds && de)  return { to: this.endOfDay(de) };
      return {};
    }

    return {}; // 'all'
  }

  private isWithin(d?: string, from?: Date, to?: Date): boolean {
    if (!from && !to) return true;
    const dt = d ? this.parseISO(d) : null;
    if (!dt) return false;
    const t  = dt.getTime();
    const f  = from ? from.getTime() : Number.NEGATIVE_INFINITY;
    const tt = to   ? to.getTime()   : Number.POSITIVE_INFINITY;
    return f <= t && t <= tt;
  }

  // ---------- Liste filtrée ----------
  readonly filtered = computed<Penalite[]>(() => {
    const rows = this.penalites();
    if (!rows?.length) return [];

    const q  = this.normalize(this.query());
    const st = this.normalize(this.statut());
    const { from, to } = this.getPeriod(this.dateMode(), this.dateSpecific(), this.dateStart(), this.dateEnd());

    return rows.filter(p => {
      // Recherche: chauffeur + référence contrat
      let okSearch = true;
      if (q) {
        const tit = this.normalize(p?.chauffeur);
        const ref = this.normalize(p?.reference_contrat);
        okSearch = tit.includes(q) || ref.includes(q);
      }

      // Statut
      let okStatut = true;
      if (st) {
        const val = this.normalize(p?.statut_penalite);
        okStatut = val === st;
      }

      // Date (sur date_paiement_manquee)
      const okDate = this.isWithin(p?.date_paiement_manquee, from, to);

      return okSearch && okStatut && okDate;
    });
  });

  // ---------- Pagination ----------
  readonly pageSize   = signal(25);
  readonly pageIndex  = signal(0);
  readonly total      = computed(() => this.filtered().length);
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly pageStart  = computed(() => this.pageIndex() * this.pageSize());
  readonly pageEnd    = computed(() => Math.min(this.pageStart() + this.pageSize(), this.total()));
  readonly paged      = computed(() => this.filtered().slice(this.pageStart(), this.pageEnd()));

  private _keepInRange = effect(() => {
    if (this.pageIndex() > this.totalPages() - 1) this.pageIndex.set(0);
  });

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

  goToPage(i: number) {
    const clamped = Math.max(0, Math.min(i, this.totalPages() - 1));
    this.pageIndex.set(clamped);
  }
  prev(){ this.goToPage(this.pageIndex() - 1); }
  next(){ this.goToPage(this.pageIndex() + 1); }
  changePageSize(size: number){ this.pageSize.set(size); this.pageIndex.set(0); }

  // ---------- EXPORTS ----------
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

  private number(v: unknown): string {
    const n = Number(v ?? 0);
    return isFinite(n) ? n.toLocaleString('fr-FR') : '';
  }

  private fmtDate(s?: string): string {
    const d = s ? new Date(s) : null;
    return d && !isNaN(+d) ? d.toLocaleDateString('fr-FR') : '';
  }

  private mapRow(p: Penalite) {
    return {
      'Chauffeur': p?.chauffeur ?? '',
      'Référence contrat': p?.reference_contrat ?? '',
      'Statut pénalité': p?.statut_penalite ?? '',
      'Type': p?.type_penalite ?? '',
      'Date paiement manquée': this.fmtDate(p?.date_paiement_manquee),
      'Montant pénalité': this.number(p?.montant_penalite),
      'Montant payé': this.number(p?.montant_paye),
      'Montant restant': this.number(p?.montant_restant),
    };
  }

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

  exportCSV(allFiltered: boolean = true) {
    const data = (allFiltered ? this.filtered() : this.paged()).map(p => this.mapRow(p));
    const csv = this.toCSV(data, ',');
    this.download(csv, `penalites_${this.nowSlug()}.csv`, 'text/csv;charset=utf-8;');
  }

  exportExcel(allFiltered: boolean = true) {
    const data = (allFiltered ? this.filtered() : this.paged()).map(p => this.mapRow(p));
    const ws = XLSX.utils.json_to_sheet(data, { skipHeader: false });
    ws['!cols'] = [
      { wch: 24 }, // Chauffeur
      { wch: 20 }, // Référence
      { wch: 18 }, // Statut pénalité
      { wch: 10 }, // Type
      { wch: 18 }, // Date manquée
      { wch: 16 }, // Montant pénalité
      { wch: 16 }, // Montant payé
      { wch: 16 }, // Montant restant
    ];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Penalites');
    XLSX.writeFile(wb, `penalites_${this.nowSlug()}.xlsx`);
  }

  refresh(){ this.penaliteService.fetchPenalites(); }

  openPaiementPenaliteDialog(p: Penalite) {
    this.dialog.open(AddPaiementPenalite, {
      width: '90vw',
      maxWidth: '520px',
      panelClass: 'penalite_modal',
      disableClose: true,
      data: { penalite: p }
    }).afterClosed().subscribe(res => {
      if (res) {
        // on rafraîchit pour voir la pénalité mise à jour
        this.penaliteService.fetchPenalites();
      }
    });
  }
}
