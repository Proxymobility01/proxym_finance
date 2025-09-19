import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormGroup, FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';
import { Lease, PaiementLeasePayload } from '../../models/lease.model';
import {LeaseService} from '../../services/lease';
import {ContratChauffeurService} from '../../services/contrat-chauffeur';

@Component({
  selector: 'app-add-paiement-lease',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './add-paiement-lease.html',
  styleUrl: './add-paiement-lease.css'
})
export class AddPaiementLeaseComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<AddPaiementLeaseComponent>);
  private readonly leaseService = inject(LeaseService);
  private readonly contratService = inject(ContratChauffeurService);

  readonly contrats = this.contratService.contratsCh;
  readonly isLoadingLeases = this.leaseService.isLoadingLeases;
  readonly isSubmitting = this.leaseService.isLeaseSubmitting;
  readonly submitError = this.leaseService.isLeaseSubmitError;

  paiementForm = new FormGroup({
    contrat_id: new FormControl<number | null>(null, Validators.required),
    montant_moto: new FormControl('', [Validators.required, Validators.min(1)]),
    montant_batterie: new FormControl('', [Validators.required, Validators.min(1)]),
    methode_paiement: new FormControl('', Validators.required),
    date_concernee: new FormControl('', Validators.required),
    date_limite: new FormControl('', Validators.required),
    reference_transaction: new FormControl('', [
      Validators.maxLength(100)
    ])
  });

  // Getters pratiques
  get contratIdCtrl() { return this.paiementForm.get('contrat_id') as FormControl; }
  get montantMotoCtrl() { return this.paiementForm.get('montant_moto') as FormControl; }
  get montantBatterieCtrl() { return this.paiementForm.get('montant_batterie') as FormControl; }
  get methodeCtrl() { return this.paiementForm.get('methode_paiement') as FormControl; }
  get dateConcerneeCtrl() { return this.paiementForm.get('date_concernee') as FormControl; }
  get dateLimiteCtrl() { return this.paiementForm.get('date_limite') as FormControl; }
  get refCtrl() { return this.paiementForm.get('reference_transaction') as FormControl; }

  ngOnInit(): void {
    this.leaseService.fetchLeases();
  }

  submit() {
    if (this.paiementForm.invalid) {
      this.paiementForm.markAllAsTouched();
      return;
    }

    const payload: Omit<PaiementLeasePayload, 'id'> = {
      contrat_id: this.contratIdCtrl.value!,
      montant_moto: this.montantMotoCtrl.value!,
      montant_batterie: this.montantBatterieCtrl.value!,
      methode_paiement: this.methodeCtrl.value!,
      date_concernee: this.dateConcerneeCtrl.value!,
      date_limite: this.dateLimiteCtrl.value!,
      reference_transaction: this.refCtrl.value || ''
    };

    this.leaseService.registerLease(payload, () => {
      this.dialogRef.close('refresh');
    });
  }

  close() {
    this.dialogRef.close();
  }
}
