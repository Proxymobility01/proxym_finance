# gestion_hospitaliere/settings/prod.py
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env.prod')
from .base import *
DEBUG = False
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

