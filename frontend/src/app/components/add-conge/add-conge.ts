// src/app/components/add-conge/add-conge.ts
import { Component, HostListener, Inject, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators, ValidatorFn, AbstractControl } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NgClass } from '@angular/common';


import {CongeDialogData, CongePayload, Mode, MOTIF_SAFE_REGEX} from '../../models/conge.model';
import { ContratChauffeurService } from '../../services/contrat-chauffeur';
import {CongeService} from '../../services/conge';

@Component({
  selector: 'app-add-conge',
  standalone: true,
  imports: [ReactiveFormsModule, NgClass],
  templateUrl: './add-conge.html',
  styleUrl: './add-conge.css'
})
export class AddConge {
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

  // --- Form
  form = new FormGroup({
    contrat_id:  new FormControl<number | null>(null, [Validators.required]),
    date_debut:  new FormControl<string>('', [Validators.required]),
    date_fin:    new FormControl<string>('', [Validators.required]),
    motif: new FormControl<string>('', [
      Validators.maxLength(500),
      Validators.pattern(MOTIF_SAFE_REGEX),
      this.noAngleBracketsValidator()
    ]),
  }, { validators: [this.dateRangeValidator()], updateOn: 'blur' });

  // Getters pratiques
  get contrat_id() { return this.form.get('contrat_id') as FormControl<number | null>; }
  get date_debut() { return this.form.get('date_debut') as FormControl<string>; }
  get date_fin()   { return this.form.get('date_fin')   as FormControl<string>; }
  get motif()      { return this.form.get('motif')      as FormControl<string>; }

  // Label affiché pour chaque contrat dans la liste
  readonly contratLabel = (c: any) =>
    `${c?.reference ?? 'REF'} — ${c?.nom_chauffeur ?? 'Chauffeur'}${c?.date_signature ? ' (' + new Date(c.date_signature).toLocaleDateString('fr-FR') + ')' : ''}`;

  constructor(@Inject(MAT_DIALOG_DATA) public data: CongeDialogData) {
    // Mode + pré-remplissage
    const mode = data?.mode ?? 'create';
    this._mode.set(mode);

    // Récupérer la liste des contrats si ce n'est pas déjà en cache
    this.contratService.fetchContratChauffeur();

    // Pré-remplir si édition
    if (mode === 'edit' && data?.conge) {
      this.form.patchValue({
        contrat_id: data.conge.contrat_id ?? null,
        date_debut: data.conge.date_debut ?? '',
        date_fin:   data.conge.date_fin ?? '',
        motif:      data.conge.motif ?? ''
      });
      // Désactiver le select contrat en édition
      this.contrat_id.disable({ emitEvent: false });
    }
  }

  // Construction payload (toujours JSON)
  private buildPayload(): Omit<CongePayload, 'id'> {
    return {
      contrat_id: Number(this.contrat_id.value),
      date_debut: String(this.date_debut.value),
      date_fin:   String(this.date_fin.value),
      motif:      String(this.motif.value ?? '').trim()
    };
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload = this.buildPayload();

    if (this.mode() === 'create') {
      this.congeService.registerConge(payload, (res) => this.dialogRef.close(res));
    } else {
      const id = this.data?.id;
      if (!id) {
        console.error('ID manquant pour la mise à jour du congé');
        return;
      }
      // En édition: ne pas envoyer contrat_id si le champ est disabled (protège contre une modif côté client)
      const { contrat_id, ...rest } = payload;
      this.congeService.updateConge(id, rest, (res) => this.dialogRef.close(res));
    }
  }

  cancel() { this.dialogRef.close(); }

  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
