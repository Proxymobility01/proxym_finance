import {Component, inject} from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogRef,
} from '@angular/material/dialog';
import {FormControl, FormGroup, ReactiveFormsModule, Validators} from '@angular/forms';
import { UpperCasePipe} from '@angular/common';
import {PenaliteService} from '../../services/penalite';
type DialogData = { id: number; chauffeur?: string; type_penalite: 'legere'|'grave' };
@Component({
  selector: 'app-annuler-penalite',
  imports: [
    ReactiveFormsModule,
    UpperCasePipe,
  ],
  templateUrl: './annuler-penalite.html',
  styleUrl: './annuler-penalite.css'
})
export class AnnulerPenalite {
  private readonly dialogRef = inject(MatDialogRef<AnnulerPenalite>);
  readonly data = inject<DialogData>(MAT_DIALOG_DATA);
  private readonly penaliteService = inject(PenaliteService);

  submitting = this.penaliteService.cancelError;
  submitError = this.penaliteService.isCancelling;
  form = new FormGroup({
    justificatif: new FormControl<string>('', { validators: [Validators.required, Validators.minLength(5)] })
  });

  close() { this.dialogRef.close(); }
  submit() {
    if (this.form.invalid) return;
    this.dialogRef.close({ justificatif: this.form.value.justificatif?.trim() });
  }
}
