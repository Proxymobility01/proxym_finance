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
import { GarantPayload, VALIDATION } from '../../models/garant.model';
import { norm } from '../../shared/utils';

type FileKind = 'photo' | 'plan_localisation' | 'cni_recto' | 'cni_verso' | 'justif_activite';

@Component({
  selector: 'app-add-garant',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './add-garant.html',
  styleUrl: './add-garant.css'
})
export class AddGarant {
  private readonly dialogRef = inject(MatDialogRef<AddGarant>);
  readonly isLoading = signal(false);

  // états d’upload (par champ)
  readonly uploading = signal<Record<FileKind, boolean>>({
    photo: false, plan_localisation: false, cni_recto: false, cni_verso: false, justif_activite: false
  });
  readonly uploadError = signal<Record<FileKind, string | null>>({
    photo: null, plan_localisation: null, cni_recto: null, cni_verso: null, justif_activite: null
  });

  // --- VALIDATEURS CUSTOM (pour ajouter min/max + pattern proprement) ---
  private safeTextValidators(required = false) {
    const list = [
      Validators.minLength(VALIDATION.MIN_TEXT),
      Validators.maxLength(VALIDATION.MAX_TEXT),
      Validators.pattern(VALIDATION.SAFE_TEXT_PATTERN)
    ];
    if (required) list.unshift(Validators.required);
    return list;
  }

  // Au moins 1 fichier requis (pour justif_activite)
  private atLeastOneFile(ctrl: AbstractControl): ValidationErrors | null {
    const arr = ctrl as FormArray<FormControl<string>>;
    return arr && arr.length > 0 ? null : { required: true };
  }

  // --- FORM ---
  form = new FormGroup({
    // texte
    nom:        new FormControl<string>('', this.safeTextValidators(true)),
    prenom:     new FormControl<string>('', this.safeTextValidators(false)),
    tel:        new FormControl<string>('', [Validators.pattern(VALIDATION.TELEPHONE_PATTERN)]),
    ville:      new FormControl<string>('', this.safeTextValidators(true)),
    quartier:   new FormControl<string>('', this.safeTextValidators(true)),
    profession: new FormControl<string>('', this.safeTextValidators(false)),

    // fichiers (multi) -> tableau de tokens/urls
    photo:             new FormArray<FormControl<string>>([]),
    plan_localisation: new FormArray<FormControl<string>>([]),
    cni_recto:         new FormArray<FormControl<string>>([]),
    cni_verso:         new FormArray<FormControl<string>>([]),
    justif_activite:   new FormArray<FormControl<string>>([], [this.atLeastOneFile.bind(this)]), // requis
  }, { updateOn: 'blur' });

  // getters pratiques
  get nom()        { return this.form.get('nom') as FormControl<string>; }
  get prenom()     { return this.form.get('prenom') as FormControl<string>; }
  get tel()        { return this.form.get('tel') as FormControl<string>; }
  get ville()      { return this.form.get('ville') as FormControl<string>; }
  get quartier()   { return this.form.get('quartier') as FormControl<string>; }
  get profession() { return this.form.get('profession') as FormControl<string>; }

  get photoArr()   { return this.form.get('photo') as FormArray<FormControl<string>>; }
  get planArr()    { return this.form.get('plan_localisation') as FormArray<FormControl<string>>; }
  get cniRectoArr(){ return this.form.get('cni_recto') as FormArray<FormControl<string>>; }
  get cniVersoArr(){ return this.form.get('cni_verso') as FormArray<FormControl<string>>; }
  get justifArr()  { return this.form.get('justif_activite') as FormArray<FormControl<string>>; }

  ngOnInit(): void {}

  // --- MOCK upload (remplace par vrai service) ---
  private async uploadFile(kind: FileKind, file: File): Promise<string> {
    await new Promise(r => setTimeout(r, 300));
    return `uploads/${Date.now()}_${file.name}`;
  }

  // --- Gestion MULTI fichiers ---
  async onFileChange(kind: FileKind, event: Event) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files || files.length === 0) return;

    // types autorisés
    const allowed = new Set([
      'application/pdf',
      'image/png', 'image/jpeg', 'image/jpg',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]);

    // cible (FormArray) selon le champ
    const arrMap: Record<FileKind, FormArray<FormControl<string>>> = {
      photo: this.photoArr,
      plan_localisation: this.planArr,
      cni_recto: this.cniRectoArr,
      cni_verso: this.cniVersoArr,
      justif_activite: this.justifArr
    };
    const targetArr = arrMap[kind];

    // reset erreurs + set uploading
    this.uploadError.update(e => ({ ...e, [kind]: null }));
    this.uploading.update(u => ({ ...u, [kind]: true }));

    try {
      for (const file of Array.from(files)) {
        if (!allowed.has(file.type)) {
          this.uploadError.update(e => ({ ...e, [kind]: 'Type de fichier non supporté' }));
          continue; // on saute ce fichier, on traite les autres
        }
        const token = await this.uploadFile(kind, file);
        targetArr.push(new FormControl<string>(token, { nonNullable: true }));
      }
      // justif requis -> revalider après ajout
      if (kind === 'justif_activite') this.justifArr.updateValueAndValidity();
    } catch {
      this.uploadError.update(e => ({ ...e, [kind]: 'Échec de l’upload' }));
    } finally {
      this.uploading.update(u => ({ ...u, [kind]: false }));
      // reset input pour pouvoir réuploader les mêmes noms si besoin
      input.value = '';
    }
  }

  removeFile(kind: FileKind, index: number) {
    const arr = ({
      photo: this.photoArr,
      plan_localisation: this.planArr,
      cni_recto: this.cniRectoArr,
      cni_verso: this.cniVersoArr,
      justif_activite: this.justifArr
    } as const)[kind];

    if (index >= 0 && index < arr.length) {
      arr.removeAt(index);
      if (kind === 'justif_activite') this.justifArr.updateValueAndValidity();
    }
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.isLoading.set(true);

    const payload: GarantPayload = {
      id: 0,
      nom:        norm(this.nom.value),
      prenom:     norm(this.prenom.value),
      tel:        norm((this.tel.value || '').replace(/\s+/g, '')), // garde chiffres uniquement
      ville:      norm(this.ville.value),
      quartier:   norm(this.quartier.value),
      profession: norm(this.profession.value),

      // tableaux de tokens fichiers
      photo:             this.photoArr.value,
      plan_localisation: this.planArr.value,
      cni_recto:         this.cniRectoArr.value,
      cni_verso:         this.cniVersoArr.value,
      justif_activite:   this.justifArr.value, // requis (>=1)
    };

    // TODO: GarantService.create(payload)
    this.isLoading.set(false);
    this.dialogRef.close(payload);
  }

  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
