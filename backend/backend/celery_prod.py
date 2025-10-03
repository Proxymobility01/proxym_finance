# backend/celery_prod.py
import os

# Force Django à charger les settings PROD
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.prod")

from .celery import app  # noqa: F401
