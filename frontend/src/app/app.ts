import {Component, inject, OnInit} from '@angular/core';
import { RouterOutlet } from '@angular/router';
import {AuthService} from './core/auth/auth';


@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {

}
