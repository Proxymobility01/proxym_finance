import {Component, computed, HostListener, Inject, inject, OnInit, signal} from '@angular/core';
import {
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
  AbstractControl,
  ValidationErrors
} from '@angular/forms';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {
  AssociationUserMoto,
  CONTRACT_VALIDATION,
  ContratChauffeurDialogData,
  FileKind
} from '../../models/contrat-chauffeur.model';
import {
  dateCoherenceValidator,
  engagedNotAboveTotalValidator,
  normalizeMoneyString
} from '../../shared/utils';
import {ContratChauffeurService} from '../../services/contrat-chauffeur';
import {GarantService} from '../../services/garant';
import {ContratBatterieService} from '../../services/contrat-batterie';
import {Garant} from '../../models/garant.model';
import {ContratBatterie} from '../../models/contrat-batterie.model';
import {Mode} from '../../models/conge.model';


@Component({
  selector: 'app-add-contrat-chauffeur',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './add-contrat-chauffeur.html',
  styleUrl: './add-contrat-chauffeur.css'
})
export class AddContratChauffeur implements OnInit{
  readonly dialogRef = inject(MatDialogRef<AddContratChauffeur>);
  readonly contratService = inject(ContratChauffeurService);
  readonly garantService = inject(GarantService);
  readonly contratBattService = inject(ContratBatterieService);
  readonly contratChauffeurService = inject(ContratChauffeurService);

  private readonly _mode = signal<Mode>('create');
  readonly mode = this._mode.asReadonly();

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
  private toNumOrNull(v: unknown): number | null {
    const n = typeof v === 'string' ? Number(v) : (v as number);
    return Number.isFinite(n) ? (n as number) : null;
  }

  private resolveGarantIdFromLabel(label: string | undefined | null): number | null {
    if (!label) return null;
    const list = this.garantService.garants(); // ta liste déjà fetchée
    const match = list.find(g => this.garantLabel(g) === label);
    return match?.id ?? null;
  }

  constructor(@Inject(MAT_DIALOG_DATA) public data: ContratChauffeurDialogData) {
    const mode = data?.mode ?? 'create';
    this._mode.set(mode);

  }

  ngOnInit() {
    // Initialisation des listes
    this.garantService.fetchGarants();
    this.contratBattService.fetchContratBatterie();
    this.contratService.fetchAssociationUserMoto();

    // 🟢 Si mode édition, préremplir après la création du form
    if (this.mode() === 'edit' && this.data?.contrat) {
      const c = this.data.contrat;
      const garantId =
        (c as any).garant_id ??
        this.toNumOrNull((c as any).garant) ??
        this.resolveGarantIdFromLabel(c.garant);

      // ⚠️ Utilise patchValue ici, car this.form est maintenant initialisée
      this.form.patchValue({
        association_user_moto_id: c.association_user_moto_id,
        garant_id: garantId,
        contrat_batt_id: c.contrat_batt ?? null,
        montant_total: c.montant_total?.toString(),
        montant_engage: c.montant_engage?.toString(),
        montant_par_paiement: c.montant_par_paiement?.toString(),
        date_signature: c.date_signature ?? '',
        date_debut: c.date_debut ?? '',
        date_concernee: c.date_concernee ?? '',
        date_limite: c.date_limite ?? '',
        jour_conge_total: c.jour_conge_total ?? 0,
      }, { emitEvent: false });

      // Fichiers optionnels en mode édition
      this.physChauff.clearValidators();
      this.physMoto.clearValidators();
      this.physBatt.clearValidators();
      this.physChauff.updateValueAndValidity();
      this.physMoto.updateValueAndValidity();
      this.physBatt.updateValueAndValidity();

      this.total.disable({ emitEvent: false });
      this.engage.disable({ emitEvent: false });
      this.mpp.disable({ emitEvent: false });
      this.djour.disable({ emitEvent: false });
    }

  }


  // ---------- LISTES DÉROULANTES (computed) ----------
  private garantLabel(g: Garant): string {
    const nom = (g?.nom ?? '').trim();
    const prenom = (g?.prenom ?? '').trim();
    const tel = (g?.tel ?? '').trim();
    const fullName = [nom, prenom].filter(Boolean).join(' ');
    return [fullName || '—', tel || ''].filter(Boolean).join(' — ');
  }


  private battLabel(c: ContratBatterie): string {
    if (!c) return '';
    const ref = c.reference_contrat ?? `#${c.id}`;
    const owner = c.proprietaire?.trim() || '';
    return owner ? `${ref} — ${owner}` : ref;
  }

  readonly battOptions = computed(() => {
    const list = this.contratBattService.contratsBatt() || [];
    const currentId = this.data?.contrat?.contrat_batt;
    return list
      .filter(c => !c.proprietaire || c.id === currentId)
      .map(c => ({ id: c.id, label: this.battLabel(c) }));
  });



  readonly garantOptions = computed(() =>
    (this.garantService.garants() || []).map(g => ({ id: g.id, label: this.garantLabel(g) }))
  );

  private assocLabel(a: AssociationUserMoto): string {
    if (!a) return '';
    const nom = a.nom?.trim() ?? '';
    const prenom = a.prenom?.trim() ?? '';
    const vin = a.vin?.trim() ?? '';

    const fullName = [nom, prenom].filter(Boolean).join(' ');
    return fullName && vin ? `${fullName} — ${vin}` : fullName || vin || `#${a.association_id}`;
  }

  readonly associationOptions = computed(() =>
    (this.contratChauffeurService.associations() || []).map(a => ({
      id: a.association_id,
      label: this.assocLabel(a)
    }))
  );




  // --- FORM ---
  form = new FormGroup(
    {
      // Sélecteurs (obligatoires). Dans le template: <option [ngValue]="id"> pour renvoyer un number
      association_user_moto_id: new FormControl<number | null>(null, [Validators.required]),
      garant_id:                new FormControl<number | null>(null, [Validators.required]),
      contrat_batt_id:          new FormControl<number | null>(null, [Validators.required]),

      // Montants (string -> on normalise à la soumission)
      montant_total:  new FormControl<string>('1302000', [
        Validators.required,
        Validators.maxLength(CONTRACT_VALIDATION.MAX_MONEY_LEN),
        Validators.pattern(CONTRACT_VALIDATION.MONEY_STRING_PATTERN)
      ]),
      montant_engage: new FormControl<string>('', [
        Validators.maxLength(CONTRACT_VALIDATION.MAX_MONEY_LEN),
        Validators.pattern(CONTRACT_VALIDATION.MONEY_STRING_PATTERN)
      ]),

      montant_par_paiement: new FormControl<string>('3500', [
        Validators.required,
        Validators.maxLength(CONTRACT_VALIDATION.MAX_MONEY_LEN),
        Validators.pattern(CONTRACT_VALIDATION.MONEY_STRING_PATTERN)
      ]),

      // Durée en jours (number)
      duree_jour: new FormControl<number | null>(62, [Validators.required, Validators.min(1), Validators.max(200)]),

      // Dates (string, pattern JJ/MM/AAAA ou ce que tu as dans DATE_PATTERN)
      date_signature: new FormControl<string>('',  Validators.pattern(CONTRACT_VALIDATION.DATE_PATTERN)),
      date_debut:     new FormControl<string>('',  Validators.pattern(CONTRACT_VALIDATION.DATE_PATTERN)),

      date_concernee: new FormControl<string>('', { validators: [Validators.pattern(CONTRACT_VALIDATION.DATE_PATTERN)], updateOn: 'change' }),
      date_limite:    new FormControl<string>('', { validators: [Validators.pattern(CONTRACT_VALIDATION.DATE_PATTERN)], updateOn: 'change' }),

      // Un fichier par champ (requis)
      contrat_physique_chauffeur:   new FormControl<File | null>(null, [Validators.required]),
      contrat_physique_moto_garant: new FormControl<File | null>(null, [Validators.required]),
      contrat_physique_batt_garant: new FormControl<File | null>(null, [Validators.required]),

      // Congés
      jour_conge_total: new FormControl<number | null>(30, [Validators.required, Validators.min(0), Validators.max(200)])
    },
    { validators: [dateCoherenceValidator, engagedNotAboveTotalValidator]}
  );

  // Getters pratiques
  get aum() { return this.form.get('association_user_moto_id') as FormControl<number | null>; }
  get garant() { return this.form.get('garant_id') as FormControl<number | null>; }
  get batt() { return this.form.get('contrat_batt_id') as FormControl<number | null>; }

  get total() { return this.form.get('montant_total') as FormControl<string | null>; }
  get engage() { return this.form.get('montant_engage') as FormControl<string | null>; }
  get mpp()    { return this.form.get('montant_par_paiement')     as FormControl<string | null>; }
  get djour() { return this.form.get('duree_jour') as FormControl<number | null>; }

  get sig() { return this.form.get('date_signature') as FormControl<string | null>; }
  get deb() { return this.form.get('date_debut') as FormControl<string | null>; }

  get physChauff() { return this.form.get('contrat_physique_chauffeur')   as FormControl<File | null>; }
  get physMoto()   { return this.form.get('contrat_physique_moto_garant') as FormControl<File | null>; }
  get physBatt()   { return this.form.get('contrat_physique_batt_garant') as FormControl<File | null>; }

  get conc() { return this.form.get('date_concernee') as FormControl<string | null>; }
  get lim()  { return this.form.get('date_limite') as FormControl<string | null>; }

  get conge() { return this.form.get('jour_conge_total') as FormControl<number | null>; }

  // --- Mock upload (remplacer par vrai service FormData + POST) ---
  private async uploadFile(kind: FileKind, file: File): Promise<string> {
    await new Promise(r => setTimeout(r, 500));
    return `uploads/${Date.now()}_${file.name}`;
  }


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

    const isEdit = this.mode() === 'edit';

    const montant_total        = normalizeMoneyString(this.total.value ?? '');
    const montant_engage       = normalizeMoneyString(this.engage.value ?? '');
    const montant_par_paiement = normalizeMoneyString(this.mpp.value ?? '');
    const dc = this.conc.value?.trim() || '';
    const dl = this.lim.value?.trim()  || '';

    const fd = new FormData();

    // Champs FK / numériques / dates (texte)
    fd.append('association_user_moto', String(this.aum.value));
    fd.append('garant',                String(this.garant.value));
    fd.append('contrat_batt',          String(this.batt.value));

    fd.append('montant_total',         montant_total);
    fd.append('montant_engage',        montant_engage);
    fd.append('montant_par_paiement',  montant_par_paiement);
    fd.append('date_signature',        this.sig.value!);
    fd.append('date_debut',            this.deb.value!);
    fd.append('jour_conge_total',      String(this.conge.value ?? 0));

    if (dc) fd.append('date_concernee', dc);
    if (dl) fd.append('date_limite',    dl);
    if (isEdit) {
      // 🔁 Pour l'UPDATE, le serializer attend association_user_moto_id
      fd.append('association_user_moto_id', String(this.aum.value));
    } else {
      // 🆕 Pour le CREATE, le serializer attend association_user_moto
      fd.append('association_user_moto', String(this.aum.value));
    }
    if (!isEdit) {
      fd.append('montant_total',        montant_total);
      fd.append('montant_engage',       montant_engage);
      fd.append('montant_par_paiement', montant_par_paiement);
      fd.append('duree_jour',           String(this.djour.value ?? 0));
    }

    // ⚠️ N’AJOUTE LE FICHIER QUE S’IL EXISTE
    if (this.physChauff.value instanceof File) {
      fd.append('contrat_physique_chauffeur', this.physChauff.value, this.physChauff.value.name);
    }
    if (this.physMoto.value instanceof File) {
      fd.append('contrat_physique_moto_garant', this.physMoto.value, this.physMoto.value.name);
    }
    if (this.physBatt.value instanceof File) {
      fd.append('contrat_physique_batt_garant', this.physBatt.value, this.physBatt.value.name);
    }

    if (this.mode() === 'create') {
      this.contratService.registerContratChauffeur(fd as any, res => this.dialogRef.close(res));
    } else {
      const id = this.data?.id;
      if (!id) { console.error('ID manquant pour la mise à jour'); return; }
      this.contratService.updateContratChauffeurWithFiles(id, fd, res => this.dialogRef.close(res));
    }
  }

  cancel() { this.dialogRef.close(); }
  @HostListener('document:keydown.escape') onEsc() { this.cancel(); }
}
