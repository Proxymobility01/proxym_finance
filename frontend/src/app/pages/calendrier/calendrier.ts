import {
  Component,
  OnInit,
  inject,
  signal,
  computed,
  effect,
  OnDestroy,
  AfterViewInit,
  ViewChild,
  ElementRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {CalendrierPaiementService} from '../../services/calendrier-paiement';
import {ChauffeurCalendrierItem} from '../../models/calendrier.model';


type DayCell = {
  iso: string | null;
  d: number | null;
  isPaid: boolean;
  isOff: boolean;
  isSunday: boolean;
  isToday: boolean;
};

type MonthView = {
  monthIndex: number;
  monthLabel: string;
  weeks: DayCell[][];
};

type ContratYearVM = {
  contratId: number;
  userId: string;
  nom: string;
  prenom: string;
  year: number;
  months: MonthView[];
  totals: { payes: number; conges: number };
};

@Component({
  selector: 'app-calendrier',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './calendrier.html',
  styleUrls: ['./calendrier.css'],
})
export class Calendrier implements OnInit, AfterViewInit, OnDestroy {
  private readonly service = inject(CalendrierPaiementService);

  @ViewChild('infiniteAnchor', { static: true })
  infiniteAnchor!: ElementRef<HTMLDivElement>;
  private io?: IntersectionObserver;

  // Recherche (debounce)
  search = signal<string>('');
  private searchTimer: any = null;
  onSearchChange(value: string) {
    this.search.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.service.searchCalendrier(value);
    }, 300);
  }

  // Année par contrat
  private yearByContrat = signal<Map<number, number>>(new Map());

  private readonly monthLabels = [
    'Janvier','Février','Mars','Avril','Mai','Juin',
    'Juillet','Août','Septembre','Octobre','Novembre','Décembre',
  ];
  readonly weekLabels = ['L','M','M','J','V','S','D'];

  // Exposition service
  readonly items = this.service.items;
  readonly isLoading = this.service.isLoading;
  readonly error = this.service.error;
  readonly count = this.service.backendCount;
  readonly currentPage = this.service.currentPage;
  readonly hasMore = this.service.hasMore; // <-- utile si tu l’utilises dans le template

  // VM annuelle par contrat
  readonly viewModels = computed<ContratYearVM[]>(() => {
    const items = this.items();
    if (!items?.length) return [];
    return items.map((it) => this.buildYearVM(it, this.getYearForContrat(it.contrat.id)));
  });

  ngOnInit(): void {
    this.service.fetchCalendrier();

    // Initialise l’année courante pour les nouveaux contrats
    effect(() => {
      const items = this.items();
      if (!items?.length) return;
      const yNow = new Date().getFullYear();
      const map = new Map(this.yearByContrat());
      let changed = false;

      // (Optionnel) réinitialiser la map aux ids courants pour éviter qu’elle grossisse
      const currentIds = new Set(items.map(i => i.contrat.id));
      for (const key of map.keys()) {
        if (!currentIds.has(key)) { map.delete(key); changed = true; }
      }

      for (const it of items) {
        if (!map.has(it.contrat.id)) { map.set(it.contrat.id, yNow); changed = true; }
      }
      if (changed) this.yearByContrat.set(map);
    });
  }

  ngAfterViewInit(): void {
    this.io = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting) return;
        if (this.service.isLoading() || !this.service.hasMore()) return;
        this.service.nextPage(); // append next page
      },
      { root: null, rootMargin: '600px 0px', threshold: 0.01 }
    );
    if (this.infiniteAnchor?.nativeElement) {
      this.io.observe(this.infiniteAnchor.nativeElement);
    }
  }

  ngOnDestroy(): void {
    this.io?.disconnect();
    if (this.searchTimer) clearTimeout(this.searchTimer);
  }

  // Helpers année
  getYearForContrat(contratId: number): number {
    return this.yearByContrat().get(contratId) ?? new Date().getFullYear();
  }
  prevYear(contratId: number) {
    const map = new Map(this.yearByContrat());
    map.set(contratId, this.getYearForContrat(contratId) - 1);
    this.yearByContrat.set(map);
  }
  nextYear(contratId: number) {
    const map = new Map(this.yearByContrat());
    map.set(contratId, this.getYearForContrat(contratId) + 1);
    this.yearByContrat.set(map);
  }

  // VM builders
  private buildYearVM(item: ChauffeurCalendrierItem, year: number): ContratYearVM {
    const paidSet = new Set(item.paiements?.filter(Boolean) ?? []);
    const offSet  = new Set(item.conges?.filter(Boolean) ?? []);
    const months: MonthView[] = [];
    for (let m = 0; m < 12; m++) months.push(this.buildMonthView(year, m, paidSet, offSet));
    const totals = this.computeYearTotals(year, paidSet, offSet);
    return {
      contratId: item.contrat.id,
      userId: item.contrat.user_unique_id,
      nom: item.contrat.nom_chauffeur,
      prenom: item.contrat.prenom_chauffeur,
      year,
      months,
      totals,
    };
  }

  private buildMonthView(
    year: number,
    monthIndex: number,
    paid: Set<string>,
    off: Set<string>,
  ): MonthView {
    const monthLabel = this.monthLabels[monthIndex];
    const first = new Date(Date.UTC(year, monthIndex, 1));
    const daysInMonth = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();

    const toMondayIndex = (jsDay0Sun: number) => (jsDay0Sun + 6) % 7;
    const firstCol = toMondayIndex(first.getUTCDay());

    const weeks: DayCell[][] = [];
    let week: DayCell[] = Array.from({ length: 7 }, () => this.emptyCell());

    let dayNum = 1;
    let col = firstCol;

    while (dayNum <= daysInMonth) {
      const d = new Date(Date.UTC(year, monthIndex, dayNum));
      const iso = this.toISO(d);
      const sunday = d.getUTCDay() === 0;
      const isPaid = paid.has(iso);
      const isOff  = !isPaid && off.has(iso);
      const isToday = this.isTodayUTC(d);

      week[col] = { iso, d: dayNum, isPaid, isOff, isSunday: sunday, isToday };

      dayNum++; col++;
      if (col > 6) {
        weeks.push(week);
        week = Array.from({ length: 7 }, () => this.emptyCell());
        col = 0;
      }
    }
    if (col !== 0) {
      for (let c = col; c < 7; c++) week[c] = this.emptyCell();
      weeks.push(week);
    }
    while (weeks.length < 6) weeks.push(Array.from({ length: 7 }, () => this.emptyCell()));

    return { monthIndex, monthLabel, weeks };
  }

  private computeYearTotals(year: number, paid: Set<string>, off: Set<string>) {
    const start = Date.UTC(year, 0, 1);
    const end   = Date.UTC(year, 11, 31);
    let payes = 0, conges = 0;
    for (let t = start; t <= end; t += 24 * 3600 * 1000) {
      const iso = this.toISO(new Date(t));
      if (paid.has(iso)) payes++;
      else if (off.has(iso)) conges++;
    }
    return { payes, conges };
  }

  private toISO(d: Date): string {
    const y = d.getUTCFullYear();
    const m = (d.getUTCMonth() + 1).toString().padStart(2, '0');
    const day = d.getUTCDate().toString().padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private isTodayUTC(d: Date): boolean {
    const now = new Date();
    return (
      now.getUTCFullYear() === d.getUTCFullYear() &&
      now.getUTCMonth() === d.getUTCMonth() &&
      now.getUTCDate() === d.getUTCDate()
    );
  }

  private emptyCell(): DayCell {
    return { iso: null, d: null, isPaid: false, isOff: false, isSunday: false, isToday: false };
  }

  // Helpers pour template
  yearFor(contratId: number) { return this.getYearForContrat(contratId); }
  yearMinus(contratId: number) { this.prevYear(contratId); }
  yearPlus(contratId: number) { this.nextYear(contratId); }
}
