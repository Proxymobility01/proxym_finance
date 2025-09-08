# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, Role

class RequiredLabelMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.required:
                field.label = mark_safe(f"{field.label} <span style='color:red'>*</span>")


class CustomUserCreationForm(UserCreationForm, RequiredLabelMixin):
    """
    Formulaire de création pour l'admin.
    - email = identifiant (USERNAME_FIELD)
    - mot de passe OBLIGATOIRE
    """
    class Meta:
        model = CustomUser
        fields = (
            'email',
            'nom',
            'prenom',
            'tel',
            'role',
            'password1',
            'password2',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Validation longueur ≥ 8
        self.fields['password1'].validators.append(
            MinLengthValidator(8, message=_("Le mot de passe doit contenir au moins 8 caractères."))
        )

        # Widgets/UX
        self.fields['email'].widget.attrs.update({
            'placeholder': 'ex: utilisateur@domaine.com',
            'autofocus': True,
        })
        self.fields['nom'].widget.attrs.update({'placeholder': 'NOM'})
        self.fields['prenom'].widget.attrs.update({'placeholder': 'Prénom'})
        self.fields['tel'].widget.attrs.update({'placeholder': 'Téléphone'})
        if 'role' in self.fields:
            self.fields['role'].queryset = Role.objects.all().order_by('nomRole')
            self.fields['role'].empty_label = '— Aucun rôle —'

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise ValidationError(_("L'email est requis."))
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = user.email.lower().strip()

        # set_password est déjà fait par UserCreationForm,
        # mais on normalise l'email avant save
        if commit:
            user.save()
            self.save_m2m()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Formulaire d’édition pour l’admin.
    """
    password = None  # masque le champ password hashé par défaut

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'nom',
            'prenom',
            'tel',
            'role',
            'is_active',
            'is_staff',
            'is_admin',
            'groups',
            'user_permissions',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['email'].widget.attrs.update({'placeholder': 'ex: utilisateur@domaine.com'})
        self.fields['nom'].widget.attrs.update({'placeholder': 'NOM'})
        self.fields['prenom'].widget.attrs.update({'placeholder': 'Prénom'})
        self.fields['tel'].widget.attrs.update({'placeholder': 'Téléphone'})
        if 'role' in self.fields:
            self.fields['role'].queryset = Role.objects.all().order_by('nomRole')
            self.fields['role'].empty_label = '— Aucun rôle —'

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise ValidationError(_("L'email est requis."))
        qs = CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email
