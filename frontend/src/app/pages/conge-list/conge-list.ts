// src/app/pages/conges/conge-list.ts
import { Component, OnInit, inject, signal, computed, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe, NgClass } from '@angular/common';
import * as XLSX from 'xlsx';

import { Conge } from '../../models/conge.model';
import { HighlightPipe } from '../../shared/highlight-pipe';
import {CongeService} from '../../services/conge';
import {AddConge} from '../../components/add-conge/add-conge';
import {MatDialog} from '@angular/material/dialog';

type StatusFilter =
  | ''
  | 'annule'
  | 'en attente'
  | 'approuve'
  | 'rejette'
  | 'en cours'
  | 'termine';

type DateFilterMode = 'today' | 'week' | 'month' | 'year' | 'specific' | 'range' | 'all';
type PageItem = { type: 'page'; index: number } | { type: 'dots' };

@Component({
  selector: 'app-conge-list',
  standalone: true,
  imports: [FormsModule, DatePipe, HighlightPipe],
  templateUrl: './conge-list.html',
  styleUrls: ['./conge-list.css'],
})
export class CongeList implements OnInit {
  private readonly congeService = inject(CongeService);
  readonly dialog = inject(MatDialog)

  // ---------- Filtres ----------
  readonly query        = signal<string>('');
  readonly statut       = signal<StatusFilter>('');
  readonly dateMode     = signal<DateFilterMode>('all');
  readonly dateSpecific = signal<string>(''); // YYYY-MM-DD
  readonly dateStart    = signal<string>(''); // YYYY-MM-DD
  readonly dateEnd      = signal<string>(''); // YYYY-MM-DD

  // ---------- Source ----------
  readonly conges    = this.congeService.conges;
  readonly isLoading = this.congeService.isLoadingConge;
  readonly error     = this.congeService.errorConge;

  ngOnInit() {
    this.congeService.fetchConges();
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

  private daysBetweenInclusive(d1?: string, d2?: string): number {
    if (!d1 || !d2) return 0;
    const a = new Date(d1);
    const b = new Date(d2);
    if (isNaN(+a) || isNaN(+b)) return 0;
    // normalise en date pure
    const A = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime();
    const B = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime();
    const diff = Math.floor((B - A) / (1000 * 60 * 60 * 24));
    return diff >= 0 ? diff + 1 : 0;
  }

// --- Utilitaire pour le template / export ---
  countDays(c: Conge): number {
    return this.daysBetweenInclusive(c?.date_debut, c?.date_fin);
  }

  // Intersection de périodes : [a1,a2] intersecte [b1,b2] ?
  private intersects(a1?: Date|null, a2?: Date|null, b1?: Date|null, b2?: Date|null): boolean {
    if (!a1 && !a2) return true; // pas de contrainte filtrante
    const A1 = a1 ? a1.getTime() : Number.NEGATIVE_INFINITY;
    const A2 = a2 ? a2.getTime() : Number.POSITIVE_INFINITY;
    const B1 = b1 ? b1.getTime() : Number.NEGATIVE_INFINITY;
    const B2 = b2 ? b2.getTime() : Number.POSITIVE_INFINITY;
    return Math.max(A1, B1) <= Math.min(A2, B2);
  }

  // ---------- Liste filtrée ----------
  readonly filtered = computed<Conge[]>(() => {
    const rows = this.conges();
    if (!rows?.length) return [];

    const q = this.normalize(this.query());
    const st = this.normalize(this.statut());
    const { from, to } = this.getPeriod(this.dateMode(), this.dateSpecific(), this.dateStart(), this.dateEnd());

    return rows.filter(c => {
      // Recherche
      let okSearch = true;
      if (q) {
        const tit = this.normalize(c?.chauffeur);
        const ref = this.normalize(c?.reference_contrat);
        okSearch = tit.includes(q) || ref.includes(q);
      }

      // Statut (exact sur les valeurs métiers, insensible casse/accents)
      let okStatut = true;
      if (st) {
        const val = this.normalize(c?.statut);
        okStatut = val === st;
      }

      // Période : intersection avec [date_debut, date_fin]
      const d1 = this.parseISO(c?.date_debut);
      const d2 = this.parseISO(c?.date_fin);
      const okDate = this.intersects(from ?? null, to ?? null, d1, d2);

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

  // Pages visibles condensées
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

  private mapRow(c: Conge) {
    const fmt = (s?: string) => {
      const d = s ? new Date(s) : null;
      return d && !isNaN(+d) ? d.toLocaleDateString('fr-FR') : '';
    };
    return {
      'Chauffeur': c?.chauffeur ?? '',
      'Référence contrat': c?.reference_contrat ?? '',
      'Statut': c?.statut ?? '',
      'Date début': fmt(c?.date_debut),
      'Date fin': fmt(c?.date_fin),
      'Nombre de jours': this.countDays(c),
    };
    // Si tu veux ajouter l'ID :
    // return { ID: c.id, ... }
  }

  openCongeDialog(){
    this.dialog.open(AddConge, {
      width: '90vw',
      maxWidth: '600px',
      panelClass: 'conge_modal',
      disableClose: true,
      data: { mode: 'create' }
    }).afterClosed().subscribe(res => { if (res) this.congeService.fetchConges(); });
  }

  openCongeEditDialog(conge:Conge){
    this.dialog.open(AddConge, {
      width: '90vw',
      maxWidth: '600px',
      panelClass: 'conge_modal',
      disableClose: true,
      data: { mode: 'edit', id: conge.id, conge }
    }).afterClosed().subscribe(res => { if (res) this.congeService.fetchConges(); });

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
    const data = (allFiltered ? this.filtered() : this.paged()).map(c => this.mapRow(c));
    const csv = this.toCSV(data, ','); // mets ';' si Excel FR strict
    this.download(csv, `conges_${this.nowSlug()}.csv`, 'text/csv;charset=utf-8;');
  }

  exportExcel(allFiltered: boolean = true) {
    const data = (allFiltered ? this.filtered() : this.paged()).map(c => this.mapRow(c));
    const ws = XLSX.utils.json_to_sheet(data, { skipHeader: false });
    ws['!cols'] = [
      { wch: 24 }, // Titulaire
      { wch: 20 }, // Référence
      { wch: 14 }, // Statut
      { wch: 12 }, // Début
      { wch: 12 }, // Fin
      { wch: 16 }, // Nb jours
    ];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Conges');
    XLSX.writeFile(wb, `conges_${this.nowSlug()}.xlsx`);
  }
}
