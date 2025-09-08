import { Component, HostListener, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators
} from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';
import {ContratBatteriesPayload} from '../../models/contrat-batterie.model';


@Component({
  selector: 'app-add-contrat-batterie',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './add-contrat-batterie.html',
  styleUrl: './add-contrat-batterie.css'
})
export class AddContratBatterie {
  readonly dialogRef = inject(MatDialogRef<AddContratBatterie>);
  readonly isLoading = signal(false);

  // Etat upload
  readonly uploading = signal<boolean>(false);
  readonly uploadError = signal<string | null>(null);

  // --- Helpers normalisation / parse ---
  // Transforme "1 200 000", "1,200,000", "1200000.50" -> number
  private toNumberSafe(input: string | number | null | undefined): number {
    if (typeof input === 'number') return input;
    const s = String(input ?? '').replace(/\s|,/g, '');
    if (!s) return 0;
    const n = Number(s);
    return isFinite(n) ? n : 0;
  }

  // yyyy-mm-dd simple check (on s’appuie aussi sur Validators.pattern)
  private isValidISODate(s: string | null | undefined): boolean {
    if (!s) return false;
    const m = s.match(/^\d{4}-\d{2}-\d{2}$/);
    if (!m) return false;
    const d = new Date(s);
    return !isNaN(+d) && s === d.toISOString().slice(0, 10);
  }

  // --- Validators custom ---
  private atLeastOneFile(ctrl: AbstractControl): ValidationErrors | null {
    const arr = ctrl as FormArray<FormControl<string>>;
    return arr && arr.length > 0 ? null : { required: true };
  }

  // date_debut <= date_fin && date_signature <= date_debut
  private static dateOrderValidator = (group: AbstractControl): ValidationErrors | null => {
    const sig = group.get('date_signature')?.value;
    const deb = group.get('date_debut')?.value;
    const fin = group.get('date_fin')?.value;

    const isISO = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(+new Date(s));
    if (!isISO(sig) || !isISO(deb) || !isISO(fin)) return null; // laissons les patterns champs remonter l'erreur

    const ds = new Date(sig);
    const dd = new Date(deb);
    const df = new Date(fin);

    const errors: any = {};
    if (ds > dd) errors.signatureAfterStart = true;
    if (dd > df) errors.startAfterEnd = true;

    return Object.keys(errors).length ? errors : null;
  };

  // Si montant_engage est présent/non vide, il doit être <= montant_total
  private static engagedNotAboveTotal = (group: AbstractControl): ValidationErrors | null => {
    const totalRaw = group.get('montant_total')?.value;
    const engageRaw = group.get('montant_engage')?.value;

    const norm = (v: any) => Number(String(v ?? '').replace(/\s|,/g, '') || '0');
    const total = norm(totalRaw);
    const engage = String(engageRaw ?? '').trim() === '' ? 0 : norm(engageRaw);

    if (engage > total) return { engageAboveTotal: true };
    return null;
  };

  // --- FORM ---
  form = new FormGroup(
    {
      // Montants (inputs de type texte pour permettre les espaces — on convertit à la soumission)
      montant_total:   new FormControl<string>('', [
        Validators.required,
        Validators.maxLength(15),
        Validators.pattern(/^\d{1,3}([ ,]?\d{3})*(\.\d{1,2})?$/) // 1000 | 1 000 | 1,000 | 1 000.50
      ]),
      montant_engage:  new FormControl<string>('', [
        // non requis
        Validators.maxLength(15),
        Validators.pattern(/^\d{0,3}([ ,]?\d{3})*(\.\d{1,2})?$/) // autorise vide
      ]),
      montant_caution: new FormControl<string>('', [
        Validators.required,
        Validators.maxLength(15),
        Validators.pattern(/^\d{1,3}([ ,]?\d{3})*(\.\d{1,2})?$/)
      ]),

      // Dates
      date_signature:  new FormControl<string>('', [
        Validators.required,
        Validators.pattern(/^\d{4}-\d{2}-\d{2}$/)
      ]),
      date_debut:      new FormControl<string>('', [
        Validators.required,
        Validators.pattern(/^\d{4}-\d{2}-\d{2}$/)
      ]),
      date_fin:        new FormControl<string>('', [
        Validators.required,
        Validators.pattern(/^\d{4}-\d{2}-\d{2}$/)
      ]),

      // Durée (string numérique > ex. "90")
      duree_jour:      new FormControl<string>('', [
        Validators.required,
        Validators.pattern(/^\d+$/)
      ]),

      // Fichiers (>=1 requis)
      contrat_physique_batt: new FormArray<FormControl<string>>([], [this.atLeastOneFile.bind(this)])
    },
    {
      validators: [AddContratBatterie.dateOrderValidator, AddContratBatterie.engagedNotAboveTotal],
      updateOn: 'blur'
    }
  );

  // Getters pratiques
  get total()   { return this.form.get('montant_total') as FormControl<string | null>; }
  get engage()  { return this.form.get('montant_engage') as FormControl<string | null>; }
  get caution() { return this.form.get('montant_caution') as FormControl<string | null>; }

  get sig()     { return this.form.get('date_signature') as FormControl<string | null>; }
  get deb()     { return this.form.get('date_debut') as FormControl<string | null>; }
  get fin()     { return this.form.get('date_fin') as FormControl<string | null>; }
  get djour()   { return this.form.get('duree_jour') as FormControl<string | null>; }

  get physBattArr() { return this.form.get('contrat_physique_batt') as FormArray<FormControl<string>>; }

  // --- Upload mock (remplace par vrai service FormData + POST) ---
  private async uploadFile(file: File): Promise<string> {
    await new Promise(r => setTimeout(r, 400));
    return `uploads/${Date.now()}_${file.name}`;
  }

  async onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files || files.length === 0) return;

    const allowed = new Set([
      'application/pdf',
      'image/png', 'image/jpeg', 'image/jpg',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]);

    this.uploadError.set(null);
    this.uploading.set(true);

    try {
      for (const f of Array.from(files)) {
        if (!allowed.has(f.type)) {
          this.uploadError.set('Type de fichier non supporté');
          continue;
        }
        const token = await this.uploadFile(f);
        this.physBattArr.push(new FormControl<string>(token, { nonNullable: true }));
      }
      this.physBattArr.updateValueAndValidity();
    } catch {
      this.uploadError.set('Échec de l’upload');
    } finally {
      this.uploading.set(false);
      input.value = '';
    }
  }

  removeFile(index: number) {
    if (index >= 0 && index < this.physBattArr.length) {
      this.physBattArr.removeAt(index);
      this.physBattArr.updateValueAndValidity();
    }
  }

  // --- Soumission ---
  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    // Validations supplémentaires légères (dates ISO)
    if (!this.isValidISODate(this.sig.value!) ||
      !this.isValidISODate(this.deb.value!) ||
      !this.isValidISODate(this.fin.value!)) {
      this.form.setErrors({ dateFormat: true });
      return;
    }

    this.isLoading.set(true);

    // Normalisations
    const montant_total   = this.toNumberSafe(this.total.value ?? '');
    const montant_engage  = String(this.engage.value ?? '').trim() === '' ? 0 : this.toNumberSafe(this.engage.value!);
    const montant_caution = this.toNumberSafe(this.caution.value ?? '');

    const payload: ContratBatteriesPayload = {
      id: 0,
      montant_total,
      montant_engage,      // 0 si non saisi
      montant_caution,
      date_signature: this.sig.value!,  // déjà validées pattern
      date_debut:     this.deb.value!,
      duree_jour:     this.djour.value!,// string numérique
      date_fin:       this.fin.value!,
      contrat_physique_batt: this.physBattArr.value
    };

    // TODO: POST backend via service puis close
    // this.service.create(payload).subscribe({...})
    this.isLoading.set(false);
    this.dialogRef.close(payload);
  }

  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
