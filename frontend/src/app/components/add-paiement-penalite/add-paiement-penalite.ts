import {Component, computed, Inject, inject, OnInit, signal} from '@angular/core';
import {PaiementPenalitePayload, Penalite} from '../../models/penalite.model';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {PenaliteService} from '../../services/penalite';
import {AbstractControl, FormControl, FormGroup, ReactiveFormsModule, ValidatorFn, Validators} from '@angular/forms';

type DialogData = { penalite: Penalite };

@Component({
  selector: 'app-add-paiement-penalite',
  imports: [
    ReactiveFormsModule
  ],
  templateUrl: './add-paiement-penalite.html',
  styleUrl: './add-paiement-penalite.css'
})
export class AddPaiementPenalite implements OnInit{

  private readonly dialogRef = inject(MatDialogRef<AddPaiementPenalite>);
  private readonly penaliteService = inject(PenaliteService);

  // état du service
  readonly isSubmitting = this.penaliteService.isPenaliteSubmitting;
  readonly submitError  = this.penaliteService.isPenaliteSubmitError;

  // pénalité reçue
  readonly p = signal<Penalite | null>(null);

  // helpers numériques
  readonly montantRestant = computed<number | null>(() => {
    const raw = this.p()?.montant_restant as any;
    const n = Number(raw);
    return isFinite(n) ? n : null;
  });

  // ---------- Validators
  private montantRangeValidator(): ValidatorFn {
    return (group: AbstractControl) => {
      const raw = (group.get('montant')?.value ?? '').toString().trim();
      if (!raw) return { montantRequired: true };

      const n = Number(raw);
      if (!isFinite(n) || n <= 0) return { montantInvalid: true };

      const max = this.montantRestant();
      if (max != null && n > max) return { montantTooHigh: { max } };

      return null;
    };
  }

  // ---------- Form
  form = new FormGroup({
    penalite_id: new FormControl<number | null>(null, { validators: [Validators.required], nonNullable: false }),
    montant: new FormControl<string>('', [Validators.required]),
    methode_paiement: new FormControl<string>('cash', [Validators.required]),
    reference_transaction: new FormControl<string>('', [Validators.maxLength(100)]),
    user_agence: new FormControl<number | null>(null),
  }, { validators: [this.montantRangeValidator()] });

  // Getters pratiques
  get penaliteIdCtrl() { return this.form.get('penalite_id') as FormControl<number | null>; }
  get montantCtrl() { return this.form.get('montant') as FormControl<string>; }
  get methodeCtrl() { return this.form.get('methode_paiement') as FormControl<string>; }
  get refCtrl() { return this.form.get('reference_transaction') as FormControl<string>; }


  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData) {}

  ngOnInit(): void {
    const pen = this.data?.penalite ?? null;
    this.p.set(pen);

    // Pré-remplissage
    if (pen) {
      this.form.patchValue({
        penalite_id: pen.id,
        montant: String(pen.montant_restant ?? ''),
        methode_paiement: 'cash',
      }, { emitEvent: false });
    }
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: PaiementPenalitePayload = {
      penalite_id: Number(this.penaliteIdCtrl.value),
      montant: Number(this.montantCtrl.value),
      methode_paiement: this.methodeCtrl.value!,
      reference_transaction: this.refCtrl.value || undefined,
    };

    this.penaliteService.registerPaiementPenalite(payload, (updated) => {
      this.dialogRef.close(updated); // renvoie la pénalité mise à jour
    });
  }

  close() { this.dialogRef.close(); }
}
