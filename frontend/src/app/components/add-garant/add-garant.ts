

import {Component, HostListener, Inject, inject, signal} from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {GarantDialogData, Mode, VALIDATION} from '../../models/garant.model';
import { norm } from '../../shared/utils';
import { GarantService } from '../../services/garant';
import {NgClass} from '@angular/common';

type FileKind = 'photo' | 'plan_localisation' | 'cni_recto' | 'cni_verso' | 'justif_activite';


@Component({
  selector: 'app-add-garant',
  standalone: true,
  imports: [ReactiveFormsModule, NgClass],
  templateUrl: './add-garant.html',
  styleUrl: './add-garant.css'
})
export class AddGarant {
  private readonly dialogRef = inject(MatDialogRef<AddGarant>);
  readonly garantService = inject(GarantService);

  readonly isSubmitting = this.garantService.isGarantSubmitting;
  readonly submitError  = this.garantService.isGarantSubmitError;
  readonly requireJustif = signal<boolean>(true);
  private readonly _mode = signal<Mode>('create');
  readonly mode = this._mode.asReadonly();
  readonly existing = signal<Record<FileKind, { path: string | null; url?: string | null }>>({
    photo:             { path: null, url: null },
    plan_localisation: { path: null, url: null },
    cni_recto:         { path: null, url: null },
    cni_verso:         { path: null, url: null },
    justif_activite:   { path: null, url: null },
  });

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: GarantDialogData
  ) {
    // ✅ c’est ici qu’on peut lire data
    const g = data?.garant ?? {};
    this.form.patchValue({
      nom: g.nom ?? '', prenom: g.prenom ?? '', tel: g.tel ?? '',
      ville: g.ville ?? '', quartier: g.quartier ?? '', profession: g.profession ?? '',
    });

    // set du mode et des règles associées
    const mode = data?.mode ?? 'create';
    this._mode.set(mode);
    this.requireJustif.set(mode === 'create');

    this.existing.set({
      photo:             { path: g.photo ?? null,             url: (g as any).photo_url ?? null },
      plan_localisation: { path: g.plan_localisation ?? null, url: (g as any).plan_localisation_url ?? null },
      cni_recto:         { path: g.cni_recto ?? null,         url: (g as any).cni_recto_url ?? null },
      cni_verso:         { path: g.cni_verso ?? null,         url: (g as any).cni_verso_url ?? null },
      justif_activite:   { path: g.justif_activite ?? null,   url: (g as any).justif_activite_url ?? null },
    });
  }


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


  private buildFormData(): FormData {
    const fd = new FormData();

    // Nom toujours requis
    fd.append('nom', norm(this.nom.value));

    // Facultatifs → envoyer les clés (vide si vide) pour rester compatible avec serializer strict
    fd.append('prenom', this.toNull(this.prenom.value) ? norm(this.prenom.value) : '');
    fd.append('tel', this.toNull(this.tel.value)
      ? norm((this.tel.value || '').replace(/\s+/g, ''))
      : '');
    fd.append('ville', this.toNull(this.ville.value) ? norm(this.ville.value) : '');
    fd.append('quartier', this.toNull(this.quartier.value) ? norm(this.quartier.value) : '');
    fd.append('profession', this.toNull(this.profession.value) ? norm(this.profession.value) : '');

    // Fichiers (n’ajouter que si sélectionnés)
    const F = this.files();
    if (F.photo)             fd.append('photo', F.photo);
    if (F.plan_localisation) fd.append('plan_localisation', F.plan_localisation);
    if (F.cni_recto)         fd.append('cni_recto', F.cni_recto);
    if (F.cni_verso)         fd.append('cni_verso', F.cni_verso);

    // justif_activite :
    // - create: requis → on l’exige et on l’ajoute
    // - edit: facultatif → on ne l’ajoute que si l’utilisateur a choisi un nouveau fichier
    if (this.mode() === 'create') {
      fd.append('justif_activite', F.justif_activite as File);
    } else {
      if (F.justif_activite) {
        fd.append('justif_activite', F.justif_activite);
      }
    }

    return fd;
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    // Justif obligatoire uniquement en création
    if (this.mode() === 'create' && !this.files().justif_activite) {
      this.uploadError.update(e => ({
        ...e,
        justif_activite: 'Veuillez joindre le justificatif (obligatoire).'
      }));
      return;
    }

    const fd = this.buildFormData();

    if (this.mode() === 'create') {
      this.garantService.registerGarant(fd, (res) => this.dialogRef.close(res));
    } else {
      if (!this.data?.id) {
        console.error('ID manquant pour la mise à jour');
        return;
      }
      // PATCH conseillé pour n’éditer que ce qui est envoyé
      this.garantService.updateGarant(this.data.id, fd, (res) => this.dialogRef.close(res));
    }
  }



  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
