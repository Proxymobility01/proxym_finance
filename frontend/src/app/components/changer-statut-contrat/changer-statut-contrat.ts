import { Component, inject } from '@angular/core';
import { FormGroup, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { ContratChauffeurService } from '../../services/contrat-chauffeur';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

type DialogData = {
  id: number;
  currentStatut: string;
  chauffeur?: string;
};

@Component({
  selector: 'app-changer-statut-contrat',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatProgressSpinnerModule],
  templateUrl: './changer-statut-contrat.html',
  styleUrl: './changer-statut-contrat.css'
})
export class ChangerStatutContrat {
  private readonly dialogRef = inject(MatDialogRef<ChangerStatutContrat>);
  readonly data = inject<DialogData>(MAT_DIALOG_DATA);
  private readonly contratService = inject(ContratChauffeurService);

  readonly isChanging = this.contratService.isChangingStatut;
  readonly changeError = this.contratService.changeStatutError;

  form = new FormGroup({
    nouveau_statut: new FormControl<string>(this.data.currentStatut, { validators: [Validators.required] }),
    motif: new FormControl<string>('', { validators: [Validators.required, Validators.minLength(5)] }),
  });

  close() {
    this.dialogRef.close();
  }

  submit() {
    if (this.form.invalid) return;

    const payload = {
      nouveau_statut: this.form.value.nouveau_statut!,
      motif: this.form.value.motif!.trim(),
    };

    this.contratService.changeStatutContrat(this.data.id, payload, () => {
      this.dialogRef.close({ success: true });
    });
  }
}
