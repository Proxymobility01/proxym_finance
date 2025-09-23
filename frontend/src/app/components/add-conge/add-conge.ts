// src/app/components/add-conge/add-conge.ts
import {Component, HostListener, Inject, inject, OnInit, signal} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators, ValidatorFn, AbstractControl } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NgClass } from '@angular/common';


import {
  CongeCreatePayload,
  CongeDialogData,
  CongePayload,
  CongeUpdatePayload,
  Mode,
  MOTIF_SAFE_REGEX
} from '../../models/conge.model';
import { ContratChauffeurService } from '../../services/contrat-chauffeur';
import {CongeService} from '../../services/conge';

@Component({
  selector: 'app-add-conge',
  standalone: true,
  imports: [ReactiveFormsModule, NgClass],
  templateUrl: './add-conge.html',
  styleUrl: './add-conge.css'
})
export class AddConge implements OnInit{
  // --- DI
  private readonly dialogRef = inject(MatDialogRef<AddConge>);
  private readonly congeService = inject(CongeService);
  private readonly contratService = inject(ContratChauffeurService);

  // --- Signals état
  readonly isSubmitting = this.congeService.isCongeSubmitting;
  readonly submitError  = this.congeService.isCongeSubmitError;

  private readonly _mode = signal<Mode>('create');
  readonly mode = this._mode.asReadonly();

  // --- Source pour <select> contrats (réutilise ton service existant)
  readonly contratsCh = this.contratService.contratsCh;

  // --- Validateurs
  private dateRangeValidator(): ValidatorFn {
    return (group: AbstractControl) => {
      const start = group.get('date_debut')?.value;
      const end   = group.get('date_fin')?.value;
      if (!start || !end) return null;
      const s = new Date(start), e = new Date(end);
      if (isNaN(+s) || isNaN(+e)) return null;
      return e.getTime() >= s.getTime() ? null : { dateRange: 'La date de fin doit être ≥ date de début.' };
    };
  }

  private noAngleBracketsValidator(): ValidatorFn {
    return (c: AbstractControl) => {
      const v = (c.value ?? '') as string;
      if (!v) return null;                // champ facultatif
      return /[<>]/.test(v) ? { unsafeChars: true } : null;
    };
  }

  ngOnInit() {
    this.form.valueChanges.subscribe(val => {
      const start = val.date_debut ? new Date(val.date_debut) : null;
      const nb = val.nb_jour ?? null;

      if (start && nb && !isNaN(start.getTime())) {
        // Date fin = date début + (nb_jour - 1)
        const fin = new Date(start);
        fin.setDate(fin.getDate() + nb - 1);

        // Date reprise = date fin + 1
        const reprise = new Date(fin);
        reprise.setDate(reprise.getDate() + 1);

        this.form.patchValue({
          date_fin: fin.toISOString().substring(0, 10),
          date_reprise: reprise.toISOString().substring(0, 10)
        }, { emitEvent: false });
      }
    });

    this.date_debut.valueChanges.subscribe(() => this.recomputeDates());
    this.nb_jour.valueChanges.subscribe(() => this.recomputeDates());
  }

  private recomputeDates() {
    const debut = this.date_debut.value;
    const jours = this.nb_jour.value;

    if (!debut || !jours) return;
    const start = new Date(debut);
    if (isNaN(+start)) return;

    // fin = début + (nb_jour - 1)
    const fin = new Date(start);
    fin.setDate(fin.getDate() + (Number(jours) - 1));

    // reprise = fin + 1
    const reprise = new Date(fin);
    reprise.setDate(reprise.getDate() + 1);

    const iso = (d: Date) => d.toISOString().slice(0, 10); // YYYY-MM-DD
    this.form.patchValue({
      date_fin: iso(fin),
      date_reprise: iso(reprise),
    }, { emitEvent: false });
  }


  // --- Form
  form = new FormGroup({
    contrat_id:  new FormControl<number | null>(null, [Validators.required]),
    date_debut:  new FormControl<string>('', [Validators.required]),
    date_fin:    new FormControl<string>({ value: '', disabled: true }),
    date_reprise:new FormControl<string>({ value: '', disabled: true }),
    nb_jour:     new FormControl<number | null>(null, [Validators.required, Validators.min(1)]),
    motif_conge: new FormControl<string>('', [
      Validators.maxLength(500),
      Validators.pattern(MOTIF_SAFE_REGEX),
      this.noAngleBracketsValidator()
    ]),
    statut: new FormControl<string>({ value: '', disabled: true })
  }, { updateOn: 'blur' });


  // Getters pratiques
  get contrat_id()  { return this.form.get('contrat_id')  as FormControl<number | null>; }
  get date_debut()  { return this.form.get('date_debut')  as FormControl<string>; }
  get nb_jour()     { return this.form.get('nb_jour')     as FormControl<number | null>; }
  get motif_conge() { return this.form.get('motif_conge') as FormControl<string>; }
  get date_fin()     { return this.form.get('date_fin') as FormControl<string | null>; }
  get date_reprise() { return this.form.get('date_reprise') as FormControl<string | null>; }
  get statut() { return this.form.get('statut') as FormControl<string | null>; }

  private computeDates(): { date_fin: string; date_reprise: string } | null {
    const debut = this.date_debut.value;
    const jours = this.nb_jour.value;

    if (!debut || !jours) return null;

    const start = new Date(debut);
    if (isNaN(+start)) return null;

    const fin = new Date(start);
    fin.setDate(start.getDate() + (jours - 1));

    const reprise = new Date(fin);
    reprise.setDate(fin.getDate() + 1);

    return {
      date_fin: fin.toISOString().split('T')[0],       // YYYY-MM-DD
      date_reprise: reprise.toISOString().split('T')[0]
    };
  }


  // Label affiché pour chaque contrat dans la liste
  readonly contratLabel = (c: any) =>
    `${c?.reference ?? 'REF'} — ${c?.chauffeur ?? 'Chauffeur'}${c?.date_signature ? ' (' + new Date(c.date_signature).toLocaleDateString('fr-FR') + ')' : ''}`;

  constructor(@Inject(MAT_DIALOG_DATA) public data: CongeDialogData) {
    // Mode + pré-remplissage
    const mode = data?.mode ?? 'create';
    this._mode.set(mode);

    // Récupérer la liste des contrats si ce n'est pas déjà en cache
    this.contratService.fetchContratChauffeur();

    // Pré-remplir si édition
    const c = data?.conge ?? {};
    if (mode === 'edit') {
      this.form.patchValue({
        contrat_id:   c.contrat_id_read ?? null,
        date_debut:   c.date_debut ? c.date_debut.substring(0, 10) : '',
        nb_jour:      c.nb_jour !== undefined ? Number(c.nb_jour) : null,
        motif_conge:  c.motif_conge ?? '',
      }, { emitEvent: false });

      this.date_fin.setValue(c.date_fin ? c.date_fin.substring(0, 10) : '', { emitEvent: false });
      this.date_reprise.setValue(c.date_reprise ? c.date_reprise.substring(0, 10) : '', { emitEvent: false });
      this.statut.setValue(c.statut ?? 'en_attente', { emitEvent: false });

      this.contrat_id.disable({ emitEvent: false });
      this.statut.enable({ emitEvent: false });
    }


  }

  // Construction payload (toujours JSON)
  // --- builders dédiés
  private buildCreatePayload(): CongeCreatePayload {
    return {
      contrat_id: Number(this.contrat_id.value),
      date_debut: String(this.date_debut.value),
      date_fin: String(this.date_fin.value),
      date_reprise: String(this.date_reprise.value),
      nb_jour: Number(this.nb_jour.value),
      motif_conge: String(this.motif_conge.value ?? '').trim(),
    };
  }

  private buildUpdatePayload(): CongeUpdatePayload {
    return {
      // si tu veux permettre la MAJ d’autres champs, garde-les
      // sinon tu peux envoyer uniquement { statut: this.statut.value! }
      statut: (this.statut.value ?? 'en_attente') as any,
      // Exemple si tu veux autoriser ces 3 aussi en edit (sinon retire-les) :
      date_debut: String(this.date_debut.value),
      date_fin: String(this.date_fin.value),
      date_reprise: String(this.date_reprise.value),
      nb_jour: Number(this.nb_jour.value),
      motif_conge: String(this.motif_conge.value ?? '').trim(),
    };
  }



  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    if (this.mode() === 'create') {
      const payload = this.buildCreatePayload();
      this.congeService.registerConge(payload, res => this.dialogRef.close(res));
    } else {
      const id = this.data?.id;
      if (!id) { console.error('ID manquant pour la mise à jour du congé'); return; }

      const payload = this.buildUpdatePayload();
      // si le contrat ne doit *pas* changer en edit, ne l'inclus pas dans payload
      this.congeService.updateConge(id, payload, res => this.dialogRef.close(res));
    }
  }

  cancel() { this.dialogRef.close(); }

  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
