import { Component, HostListener, inject, signal } from '@angular/core';
import {
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
  AbstractControl,
  ValidationErrors
} from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';
import { CONTRACT_VALIDATION, ContratChauffeurPayload } from '../../models/contrat-chauffeur.model';
import {
  dateCoherenceValidator,
  engagedNotAboveTotalValidator,
  normalizeFileToken,
  normalizeMoneyString
} from '../../shared/utils';
import {ContratChauffeurService} from '../../services/contrat-chauffeur';

type FileKind =
  | 'contrat_physique_chauffeur'
  | 'contrat_physique_moto_garant'
  | 'contrat_physique_batt_garant';

@Component({
  selector: 'app-add-contrat-chauffeur',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './add-contrat-chauffeur.html',
  styleUrl: './add-contrat-chauffeur.css'
})
export class AddContratChauffeur {
  readonly dialogRef = inject(MatDialogRef<AddContratChauffeur>);
  readonly contratService = inject(ContratChauffeurService);

  // Etats UI issus du service
  readonly isSubmitting = this.contratService.isContratChSubmitting;
  readonly submitError  = this.contratService.isContratChSubmitError;

  // états upload (par champ)
  readonly uploading = signal<Record<FileKind, boolean>>({
    contrat_physique_chauffeur: false,
    contrat_physique_moto_garant: false,
    contrat_physique_batt_garant: false
  });
  readonly uploadError = signal<Record<FileKind, string | null>>({
    contrat_physique_chauffeur: null,
    contrat_physique_moto_garant: null,
    contrat_physique_batt_garant: null
  });

  // --- Validators custom ---
  private atLeastOneFile(ctrl: AbstractControl): ValidationErrors | null {
    const arr = ctrl as FormArray<FormControl<string>>;
    return arr && arr.length > 0 ? null : { required: true };
  }

  // --- FORM ---
  form = new FormGroup(
    {
      // Sélecteurs (obligatoires). Dans le template: <option [ngValue]="id"> pour renvoyer un number
      association_user_moto_id: new FormControl<number | null>(null, [Validators.required]),
      garant_id:                new FormControl<number | null>(null, [Validators.required]),
      contrat_batt_id:          new FormControl<number | null>(null, [Validators.required]),

      // Montants (string -> on normalise à la soumission)
      montant_total:  new FormControl<string>('', [
        Validators.required,
        Validators.maxLength(CONTRACT_VALIDATION.MAX_MONEY_LEN),
        Validators.pattern(CONTRACT_VALIDATION.MONEY_STRING_PATTERN)
      ]),
      montant_engage: new FormControl<string>('', [
        Validators.required,
        Validators.maxLength(CONTRACT_VALIDATION.MAX_MONEY_LEN),
        Validators.pattern(CONTRACT_VALIDATION.MONEY_STRING_PATTERN)
      ]),

      // Durée en jours (number)
      duree_jour: new FormControl<number | null>(null, [Validators.required, Validators.min(1), Validators.max(200)]),

      // Dates (string, pattern JJ/MM/AAAA ou ce que tu as dans DATE_PATTERN)
      date_signature: new FormControl<string>('', [Validators.required, Validators.pattern(CONTRACT_VALIDATION.DATE_PATTERN)]),
      date_debut:     new FormControl<string>('', [Validators.required, Validators.pattern(CONTRACT_VALIDATION.DATE_PATTERN)]),

      // Un fichier par champ (requis)
      contrat_physique_chauffeur:   new FormControl<File | null>(null, [Validators.required]),
      contrat_physique_moto_garant: new FormControl<File | null>(null, [Validators.required]),
      contrat_physique_batt_garant: new FormControl<File | null>(null, [Validators.required]),

      // Congés
      jour_conge_total: new FormControl<number | null>(0, [Validators.required, Validators.min(0), Validators.max(200)])
    },
    { validators: [dateCoherenceValidator, engagedNotAboveTotalValidator], updateOn: 'blur' }
  );

  // Getters pratiques
  get aum() { return this.form.get('association_user_moto_id') as FormControl<number | null>; }
  get garant() { return this.form.get('garant_id') as FormControl<number | null>; }
  get batt() { return this.form.get('contrat_batt_id') as FormControl<number | null>; }

  get total() { return this.form.get('montant_total') as FormControl<string | null>; }
  get engage() { return this.form.get('montant_engage') as FormControl<string | null>; }
  get djour() { return this.form.get('duree_jour') as FormControl<number | null>; }

  get sig() { return this.form.get('date_signature') as FormControl<string | null>; }
  get deb() { return this.form.get('date_debut') as FormControl<string | null>; }

  get physChauff() { return this.form.get('contrat_physique_chauffeur')   as FormControl<File | null>; }
  get physMoto()   { return this.form.get('contrat_physique_moto_garant') as FormControl<File | null>; }
  get physBatt()   { return this.form.get('contrat_physique_batt_garant') as FormControl<File | null>; }

  get conge() { return this.form.get('jour_conge_total') as FormControl<number | null>; }

  // --- Mock upload (remplacer par vrai service FormData + POST) ---
  private async uploadFile(kind: FileKind, file: File): Promise<string> {
    await new Promise(r => setTimeout(r, 500));
    return `uploads/${Date.now()}_${file.name}`;
  }

  // --- Multi fichiers ---
  aumOptions: any;
  garantOptions: any;
  battOptions: any;
  onFileChange(kind: FileKind, event: Event) {
    const input = event.target as HTMLInputElement;
    const fileList = input.files;
    const file: File | null = fileList && fileList.length ? fileList.item(0) : null;

    this.uploadError.update(e => ({ ...e, [kind]: null }));
    this.uploading.update(u => ({ ...u, [kind]: true }));

    try {
      const ctrl = ({
        contrat_physique_chauffeur: this.physChauff,
        contrat_physique_moto_garant: this.physMoto,
        contrat_physique_batt_garant: this.physBatt
      } as const)[kind];

      if (!file) {
        ctrl.setValue(null);
        return;
      }

      const allowed = new Set([
        'application/pdf',
        'image/png', 'image/jpeg', 'image/jpg',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ]);

      if (!allowed.has(file.type)) {
        this.uploadError.update(e => ({ ...e, [kind]: 'Type de fichier non supporté' }));
        ctrl.setValue(null);
        input.value = '';
        return;
      }

      ctrl.setValue(file);
      ctrl.markAsDirty();
      ctrl.updateValueAndValidity();
    } finally {
      this.uploading.update(u => ({ ...u, [kind]: false }));
    }
  }

  clearFile(kind: FileKind) {
    const ctrl = ({
      contrat_physique_chauffeur: this.physChauff,
      contrat_physique_moto_garant: this.physMoto,
      contrat_physique_batt_garant: this.physBatt
    } as const)[kind];
    ctrl.setValue(null);
    ctrl.markAsDirty();
    ctrl.updateValueAndValidity();
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    // Normalisations
    const montant_total   = normalizeMoneyString(this.total.value ?? '');
    const montant_engage  = normalizeMoneyString(this.engage.value ?? '');

    // Construire le FormData attendu (un fichier par champ)
    const fd = new FormData();
    fd.append('association_user_moto_id', String(this.aum.value));
    fd.append('garant_id',                String(this.garant.value));
    fd.append('contrat_batt_id',          String(this.batt.value));

    fd.append('montant_total',  montant_total);
    fd.append('montant_engage', montant_engage);

    fd.append('date_signature', this.sig.value!);
    fd.append('date_debut',     this.deb.value!);
    fd.append('duree_jour',     String(this.djour.value ?? 0));
    fd.append('jour_conge_total', String(this.form.get('jour_conge_total')?.value ?? 0));

    fd.append('contrat_physique_chauffeur',   this.physChauff.value as File);
    fd.append('contrat_physique_moto_garant', this.physMoto.value   as File);
    fd.append('contrat_physique_batt_garant', this.physBatt.value   as File);

    // Appel service: HttpClient accepte FormData; si la signature TS est stricte, adapter le type en union FormData | Omit<...>
    // ou caster localement: (fd as any).
    this.contratService.registerContratChauffeur(fd as any, (res) => this.dialogRef.close(res));
  }

  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
