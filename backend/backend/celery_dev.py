# backend/celery_dev.py
import os

# Force Django à charger les settings DEV
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")

# Réutilise l'app Celery déclarée dans backend/celery.py
from .celery import app  # noqa: F401
