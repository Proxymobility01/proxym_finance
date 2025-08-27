# gestion_hospitaliere/settings/dev.py
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env.dev')
from .base import *
DEBUG = True


