

import { Component, HostListener, inject, signal } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';
import { VALIDATION } from '../../models/garant.model';
import { norm } from '../../shared/utils';
import { GarantService } from '../../services/garant';

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
  readonly garantService = inject(GarantService);

  readonly isSubmitting = this.garantService.isGarantSubmitting;
  readonly submitError  = this.garantService.isGarantSubmitError;

  // On stocke directement les File sélectionnés ici (un seul par champ)
  protected readonly files = signal<Record<FileKind, File | null>>({
    photo: null,
    plan_localisation: null,
    cni_recto: null,
    cni_verso: null,
    justif_activite: null,
  });

  // états d’upload local + erreurs de sélection (optionnels)
  readonly uploading = signal<Record<FileKind, boolean>>({
    photo: false, plan_localisation: false, cni_recto: false, cni_verso: false, justif_activite: false
  });
  readonly uploadError = signal<Record<FileKind, string | null>>({
    photo: null, plan_localisation: null, cni_recto: null, cni_verso: null, justif_activite: null
  });

  private safeTextValidators(required = false) {
    const list = [
      Validators.minLength(VALIDATION.MIN_TEXT),
      Validators.maxLength(VALIDATION.MAX_TEXT),
      Validators.pattern(VALIDATION.SAFE_TEXT_PATTERN)
    ];
    if (required) list.unshift(Validators.required);
    return list;
  }

  // --- FORM : uniquement les champs texte (les fichiers sont gérés via `files`)
  form = new FormGroup({
    nom:        new FormControl<string>('', this.safeTextValidators(true)),
    prenom:     new FormControl<string>('', this.safeTextValidators(false)),
    tel:        new FormControl<string>('', [Validators.pattern(VALIDATION.TELEPHONE_PATTERN)]),
    ville:      new FormControl<string>('', this.safeTextValidators(true)),
    quartier:   new FormControl<string>('', this.safeTextValidators(true)),
    profession: new FormControl<string>('', this.safeTextValidators(false)),
  }, { updateOn: 'blur' });

  // getters pratiques
  get nom() { return this.form.get('nom') as FormControl<string>; }
  get prenom() { return this.form.get('prenom') as FormControl<string>; }
  get tel() { return this.form.get('tel') as FormControl<string>; }
  get ville() { return this.form.get('ville') as FormControl<string>; }
  get quartier() { return this.form.get('quartier') as FormControl<string>; }
  get profession() { return this.form.get('profession') as FormControl<string>; }

  // Sélection d’un fichier (on garde le File, on ne fabrique plus de "token")
  onFileChange(kind: FileKind, event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files[0] ? input.files[0] : null;

    this.uploadError.update(e => ({ ...e, [kind]: null }));
    this.uploading.update(u => ({ ...u, [kind]: true }));

    try {
      if (!file) {
        this.files.update(f => ({ ...f, [kind]: null }));
        return;
      }

      // types autorisés (adapte si nécessaire)
      const allowed = new Set([
        'application/pdf',
        'image/png', 'image/jpeg', 'image/jpg',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ]);

      if (!allowed.has(file.type)) {
        this.uploadError.update(e => ({ ...e, [kind]: 'Type de fichier non supporté' }));
        input.value = '';
        return;
      }

      // On garde simplement le File en mémoire
      this.files.update(f => ({ ...f, [kind]: file }));
    } catch {
      this.uploadError.update(e => ({ ...e, [kind]: 'Échec de la sélection du fichier' }));
    } finally {
      this.uploading.update(u => ({ ...u, [kind]: false }));
      // on peut laisser la valeur pour permettre de remplacer, ou reset si tu préfères
      // input.value = '';
    }
  }

  clearFile(kind: FileKind) {
    this.files.update(f => ({ ...f, [kind]: null }));
  }

  private toNull(s: string | null | undefined): string | null {
    const v = String(s ?? '').trim();
    return v ? v : null;
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    if (!this.files().justif_activite) {
      this.uploadError.update(e => ({ ...e, justif_activite: 'Veuillez joindre le justificatif (obligatoire).' }));
      return;
    }

    const fd = new FormData();

    // Obligatoire
    fd.append('nom', norm(this.nom.value));

    // ⚠️ TOUJOURS ENVOYER les clés prenom et tel (même si vides)
    // -> évite "Ce champ est obligatoire."
    fd.append('prenom', this.toNull(this.prenom.value) ? norm(this.prenom.value) : '');
    fd.append('tel', this.toNull(this.tel.value) ? norm((this.tel.value || '').replace(/\s+/g, '')) : '');

    // Facultatifs : ville, quartier, profession (envoie "" si vide pour garder la clé)
    fd.append('ville', this.toNull(this.ville.value) ? norm(this.ville.value) : '');
    fd.append('quartier', this.toNull(this.quartier.value) ? norm(this.quartier.value) : '');
    fd.append('profession', this.toNull(this.profession.value) ? norm(this.profession.value) : '');

    // Fichiers
    const F = this.files();
    if (F.photo)             fd.append('photo', F.photo);
    if (F.plan_localisation) fd.append('plan_localisation', F.plan_localisation);
    if (F.cni_recto)         fd.append('cni_recto', F.cni_recto);
    if (F.cni_verso)         fd.append('cni_verso', F.cni_verso);
    fd.append('justif_activite', F.justif_activite as File); // requis côté UI

    // Utilise bien la version FormData du service
    this.garantService.registerGarant(fd, (res) => {
      this.dialogRef.close(res);
    });
  }



  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
