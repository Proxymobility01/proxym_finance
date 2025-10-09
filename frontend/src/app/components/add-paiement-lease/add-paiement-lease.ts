import {Component, OnInit, inject, signal, computed} from '@angular/core';
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
  readonly contratService = inject(ContratChauffeurService);

  readonly contrats = this.contratService.contratsCh;
  readonly contratsEncours = computed(() =>
    this.contrats().filter(c => String(c.statut).toLowerCase() === 'encours')
  );
  readonly isLoadingLeases = this.leaseService.isLoadingLeases;
  readonly isSubmitting = this.leaseService.isLeaseSubmitting;
  readonly submitError = this.leaseService.isLeaseSubmitError;

  paiementForm = new FormGroup({
    contrat_id: new FormControl<number | null>(null, Validators.required),
    montant_moto: new FormControl('', [Validators.required, Validators.min(1)]),
    montant_batt: new FormControl('', [Validators.required, Validators.min(1)]),
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
  get montantBatterieCtrl() { return this.paiementForm.get('montant_batt') as FormControl; }
  get methodeCtrl() { return this.paiementForm.get('methode_paiement') as FormControl; }
  get dateConcerneeCtrl() { return this.paiementForm.get('date_concernee') as FormControl; }
  get dateLimiteCtrl() { return this.paiementForm.get('date_limite') as FormControl; }
  get refCtrl() { return this.paiementForm.get('reference_transaction') as FormControl; }


  ngOnInit(): void {
    this.contratService.fetchContratChauffeur();

    this.methodeCtrl.setValue('espece');
    this.contratIdCtrl.valueChanges.subscribe((contratId) => {
      if (!contratId) return;
      const contrat = this.contrats().find(c => c.id === contratId);
      if (!contrat) return;

      // Montant moto
      const montantMoto = Number(contrat.montant_engage) > 0
        ? String(contrat.montant_engage)
        : String(contrat.montant_par_paiement);

      // Montant batterie
      const montantBatt = Number(contrat.montant_engage_batt) > 0
        ? String(contrat.montant_engage_batt)
        : String(contrat.montant_par_paiement_batt);

      this.montantMotoCtrl.setValue(montantMoto);
      this.montantBatterieCtrl.setValue(montantBatt);

      // Dates
      this.dateConcerneeCtrl.setValue(contrat.date_concernee);
      this.dateLimiteCtrl.setValue(contrat.date_limite);
    });
  }



  submit() {
    if (this.paiementForm.invalid) {
      this.paiementForm.markAllAsTouched();
      return;
    }

    const payload: Omit<PaiementLeasePayload, 'id'> = {
      contrat_id: this.contratIdCtrl.value!,
      montant_moto: this.montantMotoCtrl.value!,
      montant_batt: this.montantBatterieCtrl.value!,
      methode_paiement: this.methodeCtrl.value!,
      date_paiement_concerne: this.dateConcerneeCtrl.value!,
      date_limite_paiement: this.dateLimiteCtrl.value!,
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
