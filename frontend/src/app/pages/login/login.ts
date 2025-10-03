import { Component, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HttpErrorResponse } from '@angular/common/http';
import {AuthService} from '../../core/auth/auth';
import {NgIf} from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private snackBar = inject(MatSnackBar);

  loginForm: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    rememberMe: [false]
  });



  onSubmit() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    const { email, password } = this.loginForm.value;

    this.auth.login(email, password).subscribe({
      next: (res) => {
        if (res) {
          this.snackBar.open('Connexion réussie', 'Fermer', { duration: 3000 });
          this.router.navigate(['/contrat/chauffeur']);
        }
      },
      error: (err: HttpErrorResponse) => {
        let msg = 'Erreur de connexion';
        if (err.status === 401) {
          msg = 'Email ou mot de passe incorrect';
        }
        this.snackBar.open(msg, 'Fermer', { duration: 4000 });
      }
    });
  }

  get isLoading() {
    return this.auth.isLoginLoading();
  }
}
