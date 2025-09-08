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
  readonly isLoading = signal(false);

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

      // CONTRATS PHYSIQUES (multi, requis: >= 1 fichier)
      contrat_physique_chauffeur:   new FormArray<FormControl<string>>([], [this.atLeastOneFile.bind(this)]),
      contrat_physique_moto_garant: new FormArray<FormControl<string>>([], [this.atLeastOneFile.bind(this)]),
      contrat_physique_batt_garant: new FormArray<FormControl<string>>([], [this.atLeastOneFile.bind(this)]),

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

  get physChauffArr()   { return this.form.get('contrat_physique_chauffeur')   as FormArray<FormControl<string>>; }
  get physMotoArr()     { return this.form.get('contrat_physique_moto_garant') as FormArray<FormControl<string>>; }
  get physBattArr()     { return this.form.get('contrat_physique_batt_garant') as FormArray<FormControl<string>>; }

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
  async onFileChange(kind: FileKind, event: Event) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files || files.length === 0) return;

    const allowed = new Set([
      'application/pdf',
      'image/png', 'image/jpeg', 'image/jpg',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]);

    const arrMap: Record<FileKind, FormArray<FormControl<string>>> = {
      contrat_physique_chauffeur: this.physChauffArr,
      contrat_physique_moto_garant: this.physMotoArr,
      contrat_physique_batt_garant: this.physBattArr
    };
    const targetArr = arrMap[kind];

    this.uploadError.update(e => ({ ...e, [kind]: null }));
    this.uploading.update(u => ({ ...u, [kind]: true }));

    try {
      for (const f of Array.from(files)) {
        if (!allowed.has(f.type)) {
          this.uploadError.update(e => ({ ...e, [kind]: 'Type de fichier non supporté' }));
          continue;
        }
        const token = await this.uploadFile(kind, f);
        targetArr.push(new FormControl<string>(token, { nonNullable: true })); // ✅ non-nullable
      }
      // revalider (requis)
      targetArr.updateValueAndValidity();
    } catch {
      this.uploadError.update(e => ({ ...e, [kind]: 'Échec de l’upload' }));
    } finally {
      this.uploading.update(u => ({ ...u, [kind]: false }));
      // reset pour pouvoir réuploader les mêmes noms
      input.value = '';
    }
  }

  removeFile(kind: FileKind, index: number) {
    const arr = ({
      contrat_physique_chauffeur: this.physChauffArr,
      contrat_physique_moto_garant: this.physMotoArr,
      contrat_physique_batt_garant: this.physBattArr
    } as const)[kind];

    if (index >= 0 && index < arr.length) {
      arr.removeAt(index);
      arr.updateValueAndValidity();
    }
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.isLoading.set(true);

    // helpers
    const mapFiles = (arr: FormArray<FormControl<string>>) =>
      arr.value.map(t => normalizeFileToken(t));

    const payload: ContratChauffeurPayload = {
      id: 0,
      association_user_moto_id: Number(this.aum.value),
      garant_id: Number(this.garant.value),
      contrat_batt_id: Number(this.batt.value),

      montant_total:  normalizeMoneyString(this.total.value ?? ''),
      montant_engage: normalizeMoneyString(this.engage.value ?? ''),

      date_signature: this.sig.value!, // déjà validées par pattern + validator de cohérence
      date_debut:     this.deb.value!,

      duree_jour: Number(this.djour.value ?? 0),

      // tableaux de tokens (REQUIRED chacun)
      contrat_physique_chauffeur:   mapFiles(this.physChauffArr),
      contrat_physique_moto_garant: mapFiles(this.physMotoArr),
      contrat_physique_batt_garant: mapFiles(this.physBattArr),

      jour_conge_total: Number(this.conge.value ?? 0)
    };

    // TODO: this.contratService.create(payload)...
    this.isLoading.set(false);
    this.dialogRef.close(payload);
  }

  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
